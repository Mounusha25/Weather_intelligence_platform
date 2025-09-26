"""
XGBoost Weather Model
Ensemble learning model for complex weather pattern recognition and severe weather prediction
Optimized for MAE reduction and severe weather event classification
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pickle
import os

try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import mean_absolute_error, mean_squared_error, classification_report
except ImportError:
    # Fallback for when packages are not installed
    xgb = None
    train_test_split = None
    StandardScaler = None

from config.config import Config

logger = logging.getLogger(__name__)


class XGBoostWeatherModel:
    """
    XGBoost model for weather prediction and severe weather classification
    Handles multi-variate feature engineering and ensemble predictions
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.regression_models: Dict[str, Dict[str, Any]] = {}  # {region: {parameter: model}}
        self.classification_model: Optional[Any] = None
        self.scalers: Dict[str, Any] = {}
        self.label_encoders: Dict[str, Any] = {}
        self.feature_columns = []
        self.last_training_time = None
        
        # XGBoost parameters from config
        self.n_estimators = config.ml.xgboost_n_estimators
        self.max_depth = config.ml.xgboost_max_depth
        self.learning_rate = config.ml.xgboost_learning_rate
        self.severe_weather_threshold = config.ml.severe_weather_threshold
    
    def create_features(self, weather_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create comprehensive feature set for XGBoost model
        
        Args:
            weather_data: Raw weather data DataFrame
            
        Returns:
            DataFrame with engineered features
        """
        df = weather_data.copy()
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['region', 'timestamp'])
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Cyclical encoding for time features
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Lag features for each numeric column
        numeric_columns = ['temperature', 'humidity', 'pressure', 'wind_speed', 'visibility']
        lag_periods = [1, 3, 6, 12, 24]  # 5min, 15min, 30min, 1h, 2h lags
        
        for col in numeric_columns:
            if col in df.columns:
                for lag in lag_periods:
                    df[f'{col}_lag_{lag}'] = df.groupby('region')[col].shift(lag)
        
        # Rolling statistics (moving averages, std)
        rolling_windows = [3, 6, 12, 24]
        
        for col in numeric_columns:
            if col in df.columns:
                for window in rolling_windows:
                    df[f'{col}_ma_{window}'] = df.groupby('region')[col].rolling(window=window, min_periods=1).mean().reset_index(0, drop=True)
                    df[f'{col}_std_{window}'] = df.groupby('region')[col].rolling(window=window, min_periods=1).std().reset_index(0, drop=True)
        
        # Weather interaction features
        if all(col in df.columns for col in ['temperature', 'humidity']):
            df['heat_index'] = self._calculate_heat_index(df['temperature'], df['humidity'])
        
        if all(col in df.columns for col in ['temperature', 'wind_speed']):
            df['wind_chill'] = self._calculate_wind_chill(df['temperature'], df['wind_speed'])
        
        if all(col in df.columns for col in ['pressure', 'temperature']):
            df['pressure_temp_ratio'] = df['pressure'] / (df['temperature'] + 273.15)  # Normalize by Kelvin
        
        # Weather severity indicators
        df['temp_extreme'] = ((df['temperature'] < 0) | (df['temperature'] > 35)).astype(int)
        df['high_wind'] = (df['wind_speed'] > 15).astype(int) if 'wind_speed' in df.columns else 0
        df['poor_visibility'] = (df['visibility'] < 5).astype(int) if 'visibility' in df.columns else 0
        
        # Pressure change rate (indicator of weather fronts)
        if 'pressure' in df.columns:
            df['pressure_change'] = df.groupby('region')['pressure'].diff()
            df['pressure_change_rate'] = df.groupby('region')['pressure_change'].rolling(window=3).mean().reset_index(0, drop=True)
        
        # Regional features (encode region as categorical)
        if 'region' in df.columns:
            region_encoder = LabelEncoder() if LabelEncoder else None
            if region_encoder:
                df['region_encoded'] = region_encoder.fit_transform(df['region'])
                self.label_encoders['region'] = region_encoder
        
        # Target variable for severe weather classification
        df['severe_weather'] = self._create_severe_weather_target(df)
        
        return df
    
    def _calculate_heat_index(self, temp_c: pd.Series, humidity: pd.Series) -> pd.Series:
        """Calculate heat index from temperature (Celsius) and humidity"""
        # Convert to Fahrenheit for calculation
        temp_f = temp_c * 9/5 + 32
        
        # Simplified heat index formula
        hi = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (humidity * 0.094))
        
        # Convert back to Celsius
        return (hi - 32) * 5/9
    
    def _calculate_wind_chill(self, temp_c: pd.Series, wind_speed: pd.Series) -> pd.Series:
        """Calculate wind chill from temperature (Celsius) and wind speed (m/s)"""
        # Convert wind speed to km/h for calculation
        wind_kmh = wind_speed * 3.6
        
        # Wind chill formula (Environment Canada)
        wc = 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp_c * (wind_kmh ** 0.16)
        
        return wc
    
    def _create_severe_weather_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Create binary target for severe weather classification
        
        Args:
            df: DataFrame with weather features
            
        Returns:
            Binary series indicating severe weather (1) or normal (0)
        """
        severe_conditions = pd.Series(0, index=df.index)
        
        # Temperature extremes
        if 'temperature' in df.columns:
            severe_conditions |= (df['temperature'] < -5) | (df['temperature'] > 40)
        
        # High wind speeds
        if 'wind_speed' in df.columns:
            severe_conditions |= (df['wind_speed'] > 20)  # > 72 km/h
        
        # Poor visibility
        if 'visibility' in df.columns:
            severe_conditions |= (df['visibility'] < 2)
        
        # Severe weather conditions (if available)
        if 'weather_condition' in df.columns:
            severe_weather_types = ['Thunderstorm', 'Tornado', 'Hurricane', 'Blizzard', 'Hail']
            severe_conditions |= df['weather_condition'].isin(severe_weather_types)
        
        return severe_conditions.astype(int)
    
    def prepare_training_data(self, df: pd.DataFrame, target_column: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target for training
        
        Args:
            df: Feature DataFrame
            target_column: Name of target column
            
        Returns:
            Tuple of (features_df, target_series)
        """
        # Remove non-feature columns
        exclude_cols = ['timestamp', 'region', 'weather_condition', target_column]
        if target_column == 'severe_weather':
            # For classification, exclude other target variables
            exclude_cols.extend(['temperature', 'humidity', 'pressure', 'wind_speed', 'visibility'])
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Handle missing values
        features_df = df[feature_cols].copy()
        features_df = features_df.fillna(features_df.median())
        
        target_series = df[target_column].copy()
        
        # Store feature columns for prediction
        self.feature_columns = feature_cols
        
        return features_df, target_series
    
    def train_regression_model(self, weather_data: pd.DataFrame, region: str, parameter: str) -> bool:
        """
        Train XGBoost regression model for specific weather parameter
        
        Args:
            weather_data: Prepared weather data with features
            region: Region identifier
            parameter: Target weather parameter
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            if xgb is None:
                logger.error("XGBoost not available")
                return False
            
            # Filter data for specific region
            region_data = weather_data[weather_data['region'] == region].copy()
            
            if len(region_data) < 100:
                logger.error(f"Insufficient data for {region}-{parameter}: {len(region_data)} points")
                return False
            
            # Prepare features and target
            X, y = self.prepare_training_data(region_data, parameter)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False  # Time series split
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Hyperparameter tuning with GridSearch
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.05, 0.1, 0.2],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0]
            }
            
            xgb_model = xgb.XGBRegressor(
                random_state=42,
                n_jobs=-1
            )
            
            # Grid search with cross-validation
            grid_search = GridSearchCV(
                xgb_model, 
                param_grid, 
                cv=3, 
                scoring='neg_mean_absolute_error',
                n_jobs=-1,
                verbose=0
            )
            
            grid_search.fit(X_train_scaled, y_train)
            
            # Get best model
            best_model = grid_search.best_estimator_
            
            # Evaluate on test set
            y_pred = best_model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            
            # Store model and scaler
            if region not in self.regression_models:
                self.regression_models[region] = {}
            
            self.regression_models[region][parameter] = {
                'model': best_model,
                'scaler': scaler,
                'best_params': grid_search.best_params_,
                'mae': mae,
                'mse': mse,
                'feature_importance': dict(zip(self.feature_columns, best_model.feature_importances_)),
                'training_samples': len(X_train)
            }
            
            logger.info(f"XGBoost regression model trained for {region}-{parameter}")
            logger.info(f"Best parameters: {grid_search.best_params_}")
            logger.info(f"Test MAE: {mae:.3f}, MSE: {mse:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training XGBoost regression model for {region}-{parameter}: {e}")
            return False
    
    def train_classification_model(self, weather_data: pd.DataFrame) -> bool:
        """
        Train XGBoost classification model for severe weather prediction
        
        Args:
            weather_data: Prepared weather data with features
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            if xgb is None:
                logger.error("XGBoost not available")
                return False
            
            # Prepare features and target for classification
            X, y = self.prepare_training_data(weather_data, 'severe_weather')
            
            if len(X) < 100:
                logger.error(f"Insufficient data for classification: {len(X)} points")
                return False
            
            # Check class balance
            class_counts = pd.Series(y).value_counts()
            logger.info(f"Class distribution: {class_counts.to_dict()}")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Calculate scale_pos_weight for class imbalance
            scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
            
            # Train XGBoost classifier
            xgb_classifier = xgb.XGBClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                n_jobs=-1
            )
            
            xgb_classifier.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = xgb_classifier.predict(X_test_scaled)
            y_pred_proba = xgb_classifier.predict_proba(X_test_scaled)[:, 1]
            
            # Classification report
            class_report = classification_report(y_test, y_pred, output_dict=True)
            
            # Store model and scaler
            self.classification_model = {
                'model': xgb_classifier,
                'scaler': scaler,
                'classification_report': class_report,
                'feature_importance': dict(zip(self.feature_columns, xgb_classifier.feature_importances_)),
                'training_samples': len(X_train),
                'scale_pos_weight': scale_pos_weight
            }
            
            logger.info("XGBoost classification model trained for severe weather prediction")
            logger.info(f"Test accuracy: {class_report['accuracy']:.3f}")
            logger.info(f"Precision (severe): {class_report['1']['precision']:.3f}")
            logger.info(f"Recall (severe): {class_report['1']['recall']:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training XGBoost classification model: {e}")
            return False
    
    def predict_parameter(self, region: str, parameter: str, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict weather parameter using trained regression model
        
        Args:
            region: Region identifier
            parameter: Weather parameter to predict
            features: Feature DataFrame
            
        Returns:
            Dictionary with predictions and model info
        """
        if (region not in self.regression_models or 
            parameter not in self.regression_models[region]):
            return {"error": f"No trained model for {region}-{parameter}"}
        
        try:
            model_info = self.regression_models[region][parameter]
            model = model_info['model']
            scaler = model_info['scaler']
            
            # Prepare features
            X = features[self.feature_columns].fillna(features.median())
            X_scaled = scaler.transform(X)
            
            # Generate predictions
            predictions = model.predict(X_scaled)
            
            return {
                "predictions": predictions.tolist(),
                "model_info": {
                    "mae": model_info['mae'],
                    "mse": model_info['mse'],
                    "training_samples": model_info['training_samples'],
                    "best_params": model_info['best_params']
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting {region}-{parameter}: {e}")
            return {"error": str(e)}
    
    def predict_severe_weather(self, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict severe weather probability using classification model
        
        Args:
            features: Feature DataFrame
            
        Returns:
            Dictionary with predictions and probabilities
        """
        if self.classification_model is None:
            return {"error": "No trained classification model"}
        
        try:
            model = self.classification_model['model']
            scaler = self.classification_model['scaler']
            
            # Prepare features
            X = features[self.feature_columns].fillna(features.median())
            X_scaled = scaler.transform(X)
            
            # Generate predictions
            predictions = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)[:, 1]  # Probability of severe weather
            
            # Apply threshold for alerts
            alert_threshold = self.severe_weather_threshold
            alerts = probabilities > alert_threshold
            
            return {
                "predictions": predictions.tolist(),
                "probabilities": probabilities.tolist(),
                "alerts": alerts.tolist(),
                "alert_threshold": alert_threshold,
                "model_info": {
                    "accuracy": self.classification_model['classification_report']['accuracy'],
                    "training_samples": self.classification_model['training_samples']
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting severe weather: {e}")
            return {"error": str(e)}
    
    def get_feature_importance(self, region: str = None, parameter: str = None) -> Dict[str, float]:
        """Get feature importance from trained models"""
        if parameter and region:
            # Get regression model importance
            if (region in self.regression_models and 
                parameter in self.regression_models[region]):
                return self.regression_models[region][parameter]['feature_importance']
        else:
            # Get classification model importance
            if self.classification_model:
                return self.classification_model['feature_importance']
        
        return {}
    
    def save_models(self, filepath: str) -> bool:
        """Save trained models to file"""
        try:
            model_data = {
                "regression_models": self.regression_models,
                "classification_model": self.classification_model,
                "scalers": self.scalers,
                "label_encoders": self.label_encoders,
                "feature_columns": self.feature_columns,
                "last_training_time": datetime.now().isoformat(),
                "config": {
                    "n_estimators": self.n_estimators,
                    "max_depth": self.max_depth,
                    "learning_rate": self.learning_rate,
                    "severe_weather_threshold": self.severe_weather_threshold
                }
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"XGBoost models saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving XGBoost models: {e}")
            return False
    
    def load_models(self, filepath: str) -> bool:
        """Load trained models from file"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.regression_models = model_data["regression_models"]
            self.classification_model = model_data["classification_model"]
            self.scalers = model_data.get("scalers", {})
            self.label_encoders = model_data.get("label_encoders", {})
            self.feature_columns = model_data.get("feature_columns", [])
            self.last_training_time = model_data.get("last_training_time")
            
            logger.info(f"XGBoost models loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading XGBoost models: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Example usage of XGBoost Weather Model
    config = Config()
    model = XGBoostWeatherModel(config)
    
    # Generate sample data
    dates = pd.date_range('2024-01-01', periods=2000, freq='5min')
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'region': ['north'] * 2000,
        'temperature': np.random.normal(20, 8, 2000) + 10 * np.sin(np.arange(2000) * 0.01),
        'humidity': np.random.normal(60, 15, 2000),
        'pressure': np.random.normal(1013, 25, 2000),
        'wind_speed': np.random.exponential(8, 2000),
        'visibility': np.random.gamma(2, 5, 2000)
    })
    
    # Create features
    featured_data = model.create_features(sample_data)
    
    # Train regression model
    success = model.train_regression_model(featured_data, 'north', 'temperature')
    print(f"Regression model trained: {success}")
    
    # Train classification model  
    success = model.train_classification_model(featured_data)
    print(f"Classification model trained: {success}")
    
    # Get feature importance
    importance = model.get_feature_importance()
    if importance:
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"Top 5 features: {top_features}")
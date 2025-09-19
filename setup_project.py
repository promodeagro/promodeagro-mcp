import os
import sys
import stat

def set_permissions(path):
    """Set read/write permissions for user and group, read for others"""
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

def create_directory_structure():
    """Create the project directory structure"""
    directories = [
        'src/data',
        'src/models',
        'src/utils',
        'src/config',
        'tests',
        'notebooks',
        'logs'
    ]
    
    for directory in directories:
        full_path = os.path.join(os.getcwd(), directory)
        os.makedirs(full_path, exist_ok=True)
        set_permissions(full_path)
        # Create __init__.py in Python package directories
        if directory.startswith('src/') or directory == 'tests':
            init_file = os.path.join(full_path, '__init__.py')
            with open(init_file, 'w') as f:
                pass
            set_permissions(init_file)

def write_file(path, content):
    """Write content to a file"""
    full_path = os.path.join(os.getcwd(), path)
    with open(full_path, 'w') as f:
        f.write(content)
    set_permissions(full_path)

def create_readme():
    content = '''# Alert Correlation System

A machine learning-based system for correlating and analyzing alerts from multiple sources.

## Features
- Intelligent alert correlation using ML
- Real-time processing capabilities
- Pattern recognition and anomaly detection
- Root cause analysis
- Visualization of alert relationships

## Setup
1. Create a virtual environment:
```python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure
- `src/`: Source code
  - `data/`: Data processing modules
  - `models/`: ML models
  - `utils/`: Utility functions
  - `config/`: Configuration files
- `tests/`: Unit tests
- `notebooks/`: Jupyter notebooks for analysis

## Usage
[Documentation will be added as components are implemented]

## Contributing
[Contributing guidelines will be added]

## License
MIT License
'''
    write_file('README.md', content)

def create_requirements():
    content = '''numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=0.24.2
tensorflow>=2.6.0
torch>=1.9.0
matplotlib>=3.4.2
seaborn>=0.11.1
pytest>=6.2.5
jupyter>=1.0.0
python-dotenv>=0.19.0
fastapi>=0.68.0
uvicorn>=0.15.0
pyyaml>=5.4.1'''
    write_file('requirements.txt', content)

def create_data_loader():
    content = '''import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

class AlertDataLoader:
    def __init__(self, config: Dict):
        self.config = config
        
    def load_alerts(self, source: str, start_time: Optional[datetime] = None, 
                    end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load alerts from specified source within given time range
        
        Args:
            source: Source identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            DataFrame containing alerts
        """
        # TODO: Implement specific data source connectors
        pass
    
    def validate_alert_data(self, alerts: pd.DataFrame) -> bool:
        """
        Validate alert data format and required fields
        
        Args:
            alerts: DataFrame containing alerts
            
        Returns:
            Boolean indicating if data is valid
        """
        required_fields = ['timestamp', 'source', 'severity', 'message']
        return all(field in alerts.columns for field in required_fields)
'''
    write_file('src/data/data_loader.py', content)

def create_correlation_model():
    content = '''import numpy as np
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class AlertCorrelationModel:
    def __init__(self, config: Dict):
        self.config = config
        self.text_vectorizer = TfidfVectorizer()
        
    def compute_alert_similarity(self, alert1: Dict, alert2: Dict) -> float:
        """
        Compute similarity between two alerts
        
        Args:
            alert1: First alert dictionary
            alert2: Second alert dictionary
            
        Returns:
            Similarity score between 0 and 1
        """
        # Compute text similarity
        text_similarity = self._compute_text_similarity(
            alert1['message'], 
            alert2['message']
        )
        
        # Compute temporal similarity
        temporal_similarity = self._compute_temporal_similarity(
            alert1['timestamp'],
            alert2['timestamp']
        )
        
        # Combine similarities (can be weighted based on config)
        return 0.7 * text_similarity + 0.3 * temporal_similarity
    
    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between alert messages"""
        vectors = self.text_vectorizer.fit_transform([text1, text2])
        return cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    
    def _compute_temporal_similarity(self, time1: float, time2: float) -> float:
        """Compute temporal similarity based on time difference"""
        time_diff = abs(time1 - time2)
        max_time_window = self.config.get('max_time_window', 3600)  # default 1 hour
        return max(0, 1 - (time_diff / max_time_window))
'''
    write_file('src/models/correlation_model.py', content)

def create_logger():
    content = '''import logging
from typing import Optional
import os
from datetime import datetime

class AlertLogger:
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("AlertCorrelation")
        level = getattr(logging, log_level.upper())
        self.logger.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if log_file specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)
'''
    write_file('src/utils/logger.py', content)

def create_config():
    content = '''from typing import Dict
import os
import yaml
from dotenv import load_dotenv

class Config:
    def __init__(self, config_path: str = None):
        load_dotenv()  # Load environment variables
        
        self.config = {
            'data_sources': {
                'log_files': {
                    'path': os.getenv('LOG_FILES_PATH', './data/logs'),
                    'format': 'json'
                },
                'metrics': {
                    'host': os.getenv('METRICS_DB_HOST', 'localhost'),
                    'port': int(os.getenv('METRICS_DB_PORT', 5432)),
                }
            },
            'model': {
                'max_time_window': 3600,  # 1 hour in seconds
                'similarity_threshold': 0.7,
                'min_cluster_size': 3
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/alert_correlation.log'
            }
        }
        
        # Override with config file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                self.config.update(file_config)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def update(self, updates: Dict):
        """Update configuration"""
        self.config.update(updates)
'''
    write_file('src/config/config.py', content)

def create_gitignore():
    content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDEs
.idea/
.vscode/
*.swp
*.swo

# Jupyter Notebook
.ipynb_checkpoints

# Logs
logs/
*.log

# Environment variables
.env

# OS specific
.DS_Store
Thumbs.db'''
    write_file('.gitignore', content)

def create_setup():
    content = '''from setuptools import setup, find_packages

setup(
    name="alert-correlation",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
        if not line.startswith("#")
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A machine learning-based alert correlation system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/alert-correlation",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)'''
    write_file('setup.py', content)

def create_test_files():
    test_data_loader = '''import pytest
from src.data.data_loader import AlertDataLoader
import pandas as pd
from datetime import datetime

def test_validate_alert_data():
    config = {}
    loader = AlertDataLoader(config)
    
    # Valid data
    valid_data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'source': ['test'],
        'severity': ['high'],
        'message': ['test alert']
    })
    assert loader.validate_alert_data(valid_data) == True
    
    # Invalid data (missing required field)
    invalid_data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'source': ['test'],
        'message': ['test alert']
    })
    assert loader.validate_alert_data(invalid_data) == False
'''
    write_file('tests/test_data_loader.py', test_data_loader)

    test_correlation_model = '''import pytest
from src.models.correlation_model import AlertCorrelationModel
from datetime import datetime

def test_compute_alert_similarity():
    config = {'max_time_window': 3600}
    model = AlertCorrelationModel(config)
    
    alert1 = {
        'message': 'Database connection timeout',
        'timestamp': 1000.0
    }
    
    alert2 = {
        'message': 'Database connection failed',
        'timestamp': 1100.0
    }
    
    similarity = model.compute_alert_similarity(alert1, alert2)
    assert 0 <= similarity <= 1
    
    # Test exact same alerts
    similarity = model.compute_alert_similarity(alert1, alert1)
    assert similarity == 1.0
'''
    write_file('tests/test_correlation_model.py', test_correlation_model)

def create_notebook():
    content = '''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Alert Correlation Analysis\\n",
    "\\n",
    "This notebook demonstrates the basic usage of the alert correlation system."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "import sys\\n",
    "sys.path.append('..')\\n",
    "\\n",
    "from src.data.data_loader import AlertDataLoader\\n",
    "from src.models.correlation_model import AlertCorrelationModel\\n",
    "from src.config.config import Config"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Load Configuration"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "source": [
    "config = Config()\\n",
    "print(config.config)"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}'''
    write_file('notebooks/exploratory_analysis.ipynb', content)

def main():
    # Create project structure
    create_directory_structure()
    
    # Create all files
    create_readme()
    create_requirements()
    create_data_loader()
    create_correlation_model()
    create_logger()
    create_config()
    create_gitignore()
    create_setup()
    create_test_files()
    create_notebook()
    
    print("Project structure and files created successfully!")
    print("\nNext steps:")
    print("1. Create a virtual environment: python -m venv venv")
    print("2. Activate the virtual environment:")
    print("   - Windows: .\\venv\\Scripts\\activate")
    print("   - Unix/MacOS: source venv/bin/activate")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Run tests: pytest tests/")

if __name__ == "__main__":
    main()
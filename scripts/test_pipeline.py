import sys
import os

sys.path.append(os.getcwd())
# Also add apps/api to path
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

try:
    print("Testing imports...")
    from src.infrastructure.ml_pipeline import MLPipeline
    from src.infrastructure.config import ProcessingConfig
    import rasterio
    import sklearn
    from skimage import feature
    
    print("Imports successful!")
    
    config = ProcessingConfig()
    pipeline = MLPipeline(config, output_dir="data/outputs")
    print("Pipeline instantiated.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

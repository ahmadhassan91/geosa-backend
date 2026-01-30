import asyncio
import sys
import os
from uuid import UUID

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

from src.infrastructure.config import processing_config

# Run ID and Dataset ID from previous attempt
RUN_ID = UUID("cb5c2447-faf2-4139-b162-88c0f2d2356c")
DATASET_ID = UUID("7b67b64e-ff62-4afb-b729-2c1487e8fb9f")

async def main():
    print(f"Manually triggering analysis for Run {RUN_ID} on Dataset {DATASET_ID}")
    
    from src.api.routes.runs import _run_analysis_task
    
    config = processing_config.as_dict
    
    try:
        await _run_analysis_task(RUN_ID, DATASET_ID, config)
        print("Task completed successfully!")
    except Exception as e:
        print(f"Task failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

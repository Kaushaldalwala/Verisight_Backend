import os
import sys
import subprocess
import uvicorn
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verisight_runner")

def main():
    logger.info("Starting VeriSight Phase 1 System...")
    
    # 1. Ensure environment variables are loaded
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        logger.warning(f"No .env file found at {env_path}. Make sure SUPABASE_URL, SUPABASE_KEY, and DATABASE_URL are set.")
    else:
        load_dotenv(env_path)
        
    # 2. Run Database Setup (Migrations and Synthetic Data)
    setup_script = os.path.join(os.path.dirname(__file__), "backend", "scripts", "setup_db.py")
    if os.path.exists(setup_script):
        logger.info("Running database setup script (setup_db.py)...")
        try:
            # We use subprocess to run it independently
            result = subprocess.run([sys.executable, setup_script], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Database setup failed:\n{result.stderr}")
                logger.error("Please verify your Supabase credentials in the .env file. The server will start, but validation may fail.")
            else:
                logger.info("Database setup completed successfully.")
        except Exception as e:
            logger.error(f"Failed to execute setup_db.py: {e}")
    else:
        logger.warning(f"Setup script not found at {setup_script}. Skipping database initialization.")

    # 3. Start the Backend Server
    logger.info("Starting FastAPI server...")
    # Change working directory to backend so relative paths work properly
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    os.chdir(backend_dir)
    
    # Run uvicorn programmatically
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()

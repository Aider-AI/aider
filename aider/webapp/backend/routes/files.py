from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List

router = APIRouter()

@router.get("/", response_model=List[str])
async def list_files():
    try:
        # Get base directory
        base_dir = Path(__file__).parent.parent.parent.parent
        # List all Python files
        files = [
            str(f.relative_to(base_dir))
            for f in base_dir.rglob("*.py")
            if ".venv" not in str(f)
        ]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
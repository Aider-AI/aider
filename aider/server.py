import uvicorn
from aider.api import set_aider_args

def main():
    import sys
    # Get all args after the first one (script name)
    aider_args = sys.argv[1:]
    set_aider_args(aider_args)
    
    uvicorn.run("aider.api:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()

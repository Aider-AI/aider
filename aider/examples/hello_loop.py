"""
Hello Loop Macro

A simple macro that demonstrates looping functionality.
Usage: /macro examples/hello_loop.py [times=N] [message=text]

This will respond to the user N times with the given message.
"""

from aider.helpers import log

def main(ctx, **kwargs):
    """
    Main generator function for the hello loop macro.
    
    Args:
        ctx: The context dictionary
        **kwargs: Additional arguments from the command line
            - times: Number of times to loop (default: 1)
            - message: Message to display (default: "Hello!")
    
    Yields:
        Actions to be performed by aider
    """
    # Get parameters with defaults
    times = int(kwargs.get("times", 1))
    message = kwargs.get("message", "Hello!")
    
    # Store in context for potential future use
    ctx["vars"]["times"] = times
    ctx["vars"]["message"] = message
    
    # Initialize counter if not present
    if "loop_count" not in ctx["counters"]:
        ctx["counters"]["loop_count"] = 0
    
    # Loop the specified number of times
    for i in range(times):
        ctx["counters"]["loop_count"] += 1
        current = ctx["counters"]["loop_count"]
        total = times
        
        # Yield a log message that will be displayed in the chat
        yield log(f"{message} (loop {current}/{total})")
        
        # If we wanted to wait for user input between iterations:
        # response = yield "> Press enter to continue..."


import logging

logger = logging.getLogger(__name__.split(".")[0])



def _check_log_handler():
    
    # If logger has a handler do nothing
    if logger.handlers: return
    
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # create formatter
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    
    # add formatter to ch
    ch.setFormatter(formatter)
    
    # add ch to logger
    logger.addHandler(ch)

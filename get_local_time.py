def get_local_time():
    '''
    Returns the local time for a user's computer

    '''
    from datetime import datetime
    # Use the standard library to get a local timezone-aware datetime.
    # datetime.now().astimezone() returns the current time with the
    # system-local tzinfo attached and works reliably across Python versions.
    return datetime.now().astimezone()

if __name__ == "__main__":
    print(get_local_time())
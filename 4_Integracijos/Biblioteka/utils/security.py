import bcrypt

def hash_password(plain_password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    Returns the hashed password as a string suitable for storage in the DB.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty")

    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def check_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    Returns True if the password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # in case hashed_password is malformed
        return False

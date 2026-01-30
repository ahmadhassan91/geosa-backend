from passlib.context import CryptContext
import traceback

print("Testing hashing...")
try:
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    hash = pwd_context.hash("secret")
    print(f"Hash: {hash}")
    verify = pwd_context.verify("secret", hash)
    print(f"Verify: {verify}")
except Exception:
    traceback.print_exc()

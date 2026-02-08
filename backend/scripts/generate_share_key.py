#!/usr/bin/env python3

from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print("\nGenerated SHARE_LINK_SECRET_KEY:")
    print(f"\n{key}\n")
    print("Add this to your .env file:")
    print(f"SHARE_LINK_SECRET_KEY={key}\n")
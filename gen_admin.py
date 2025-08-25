from security import hash_password
import binascii
salt, h = hash_password("1")
print("Salt (hex):", binascii.hexlify(salt).decode())
print("Hash (hex):", binascii.hexlify(h).decode())

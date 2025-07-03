from app.utils.config import get_circle_api_key, get_entity_secret, get_entity_secret_recovery_dir
from app.core.entity_secret import register_entity_secret

def main():
    api_key = get_circle_api_key()
    entity_secret = get_entity_secret()
    recovery_dir = get_entity_secret_recovery_dir()

    print(f"Using entity secret from .env: {entity_secret}")
    register_entity_secret(api_key, entity_secret, recovery_dir)

if __name__ == "__main__":
    main()
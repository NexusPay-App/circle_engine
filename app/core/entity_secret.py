from circle.web3 import utils

def register_entity_secret(api_key: str, entity_secret: str, recovery_dir: str):
    """
    Register the entity secret with Circle using the SDK. The entity_secret should be loaded from .env.
    This will also create a recovery file in the given directory.
    """
    result = utils.register_entity_secret_ciphertext(
        api_key=api_key,
        entity_secret=entity_secret,
        recoveryFileDownloadPath=recovery_dir
    )
    print(f"Entity Secret registered with Circle. Recovery file saved in {recovery_dir}")
    return result

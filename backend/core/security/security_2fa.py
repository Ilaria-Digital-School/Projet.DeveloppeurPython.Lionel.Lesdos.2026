"""
Two-Factor Authentication (2FA) Utilities

This module provides functions for generating and verifying 2FA codes,
as well as generating QR codes for authenticator apps.
"""

import base64
import io
import logging
import secrets
from typing import List, Optional, Tuple

import pyotp
import qrcode

# Configure logger
logger = logging.getLogger(__name__)


class TwoFactorAuth:
    """Handles two-factor authentication operations."""

    def __init__(self, issuer_name: str = "Appli Budget"):
        """
        Initialize 2FA with the issuer name.

        Args:
            issuer_name: Name of the application/service (displayed in authenticator app)
        """
        self.issuer_name = issuer_name

    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new 2FA secret key.

        Returns:
            str: A base32-encoded secret key
        """
        try:
            secret = pyotp.random_base32()
            logger.debug("Generated new 2FA secret")
            return secret
        except Exception as e:
            logger.error(f"Error generating 2FA secret: {str(e)}")
            raise

    @staticmethod
    def generate_backup_codes(count: int = 8, length: int = 8) -> List[str]:
        """
        Generate a list of backup recovery codes.

        Args:
            count: Number of codes to generate
            length: Length of each code in bytes (hex output will be 2x this)

        Returns:
            List[str]: List of hex-encoded backup codes
        """
        try:
            codes = [secrets.token_hex(length) for _ in range(count)]
            logger.debug(f"Generated {count} backup codes")
            return codes
        except Exception as e:
            logger.error(f"Error generating backup codes: {str(e)}")
            raise

    @staticmethod
    def get_provisioning_uri(
        secret: str, email: str, issuer_name: str = "Appli Budget"
    ) -> str:
        """
        Generate a TOTP provisioning URI for authenticator apps.

        Args:
            secret: The 2FA secret key
            email: The user's email address
            issuer_name: Name of the application/service

        Returns:
            str: The otpauth:// URI
        """
        try:
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(name=email, issuer_name=issuer_name)
            logger.debug(f"Generated provisioning URI for {email}")
            return uri
        except Exception as e:
            logger.error(f"Error generating provisioning URI: {str(e)}")
            raise

    def generate_qr_code(
        self, secret: str, username: str, issuer_name: Optional[str] = None
    ) -> str:
        """
        Generate a QR code for the authenticator app.

        Args:
            secret: The 2FA secret key
            username: The username/email of the user
            issuer_name: Optional custom issuer name

        Returns:
            str: Data URL for the QR code image (PNG)
        """
        try:
            issuer = issuer_name or self.issuer_name

            # Create TOTP URI
            totp = pyotp.totp.TOTP(secret)
            uri = totp.provisioning_uri(name=username, issuer_name=issuer)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")

            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

        except Exception as e:
            logger.error(f"Error generating 2FA QR code: {str(e)}")
            raise

    @staticmethod
    def verify_code(
        secret: str, code: str, valid_window: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a 2FA code.

        Args:
            secret: The 2FA secret key
            code: The code to verify
            valid_window: Number of time steps to allow on either side

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            if not secret or not code:
                return False, "Missing secret or code"

            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(code, valid_window=valid_window)

            if not is_valid:
                return False, "Invalid or expired code"

            return True, None

        except Exception as e:
            logger.error(f"Error verifying 2FA code: {str(e)}")
            return False, f"Verification error: {str(e)}"


# For backward compatibility
def generate_2fa_secret() -> str:
    """Legacy function to generate a 2FA secret."""
    return TwoFactorAuth().generate_secret()


def generate_2fa_qr_code(
    secret: str, username: str, issuer_name: str = "Appli Budget"
) -> str:
    """Legacy function to generate a 2FA QR code."""
    return TwoFactorAuth(issuer_name).generate_qr_code(secret, username)


def verify_2fa_code(secret: str, code: str) -> bool:
    """Legacy function to verify a 2FA code."""
    is_valid, _ = TwoFactorAuth.verify_code(secret, code)
    return is_valid

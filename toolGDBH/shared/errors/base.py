from __future__ import annotations


class ToolGiamDinhError(Exception):
    def __init__(self, error_code: str, error_message: str, retryable: bool = False):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable


class ParseError(ToolGiamDinhError):
    pass


class RuleRegistryError(ToolGiamDinhError):
    pass


class EligibilityServiceError(ToolGiamDinhError):
    pass

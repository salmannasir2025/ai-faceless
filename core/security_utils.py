#!/usr/bin/env python3
"""
SECURITY UTILITIES
Helper functions for secure coding practices throughout the project.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any


class SecurityError(Exception):
    """Base exception for security violations."""
    pass


class PathTraversalError(SecurityError):
    """Raised when path traversal is detected."""
    pass


class InputValidationError(SecurityError):
    """Raised when input validation fails."""
    pass


# Characters that could be used for command injection
DANGEROUS_CHARS = [';', '&', '|', '`', '$', '>', '<', '!', '\n', '\r']

# Regex for detecting path traversal attempts
PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.(?:/|\\)')

# Safe alphanumeric pattern for basic validation
SAFE_ALPHANUMERIC = re.compile(r'^[a-zA-Z0-9_\-\s]+$')


def sanitize_path(path: str, base_dir: Optional[str] = None) -> str:
    """
    Sanitize a file path to prevent path traversal attacks.
    
    Args:
        path: The file path to sanitize
        base_dir: Optional base directory to restrict paths to
        
    Returns:
        Sanitized absolute path
        
    Raises:
        PathTraversalError: If path traversal is detected
    """
    if not path:
        raise PathTraversalError("Empty path provided")
    
    # Check for path traversal patterns
    if PATH_TRAVERSAL_PATTERN.search(path):
        raise PathTraversalError(f"Path traversal detected: {path}")
    
    # Convert to absolute path
    abs_path = os.path.abspath(os.path.expanduser(path))
    
    # If base_dir specified, ensure path is within it
    if base_dir:
        base_abs = os.path.abspath(base_dir)
        # Normalize paths for comparison
        abs_path_norm = os.path.normpath(abs_path)
        base_norm = os.path.normpath(base_abs)
        
        if not abs_path_norm.startswith(base_norm + os.sep) and abs_path_norm != base_norm:
            raise PathTraversalError(f"Path outside allowed directory: {path}")
    
    return abs_path


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize a filename.
    
    Args:
        filename: The filename to validate
        
    Returns:
        Sanitized filename
        
    Raises:
        InputValidationError: If filename contains dangerous characters
    """
    if not filename:
        raise InputValidationError("Empty filename")
    
    # Remove any directory components
    filename = os.path.basename(filename)
    
    # Check for dangerous characters
    for char in DANGEROUS_CHARS:
        if char in filename:
            raise InputValidationError(f"Dangerous character '{char}' in filename: {filename}")
    
    # Check for null bytes
    if '\x00' in filename:
        raise InputValidationError("Null byte in filename")
    
    return filename


def validate_topic(topic: str) -> str:
    """
    Validate documentary topic input.
    
    Args:
        topic: User-provided topic string
        
    Returns:
        Sanitized topic string
        
    Raises:
        InputValidationError: If topic contains dangerous content
    """
    if not topic or not isinstance(topic, str):
        raise InputValidationError("Topic must be a non-empty string")
    
    # Length limit
    if len(topic) > 500:
        raise InputValidationError("Topic too long (max 500 characters)")
    
    # Check for dangerous characters that could be used in injection
    for char in [';', '&', '|', '`', '$']:
        if char in topic:
            raise InputValidationError(f"Invalid character '{char}' in topic")
    
    # Strip control characters except newlines
    topic = ''.join(char for char in topic if char == '\n' or ord(char) >= 32)
    
    return topic.strip()


def safe_json_load(file_path: str, max_size: int = 10 * 1024 * 1024) -> Any:
    """
    Safely load JSON from file with size limits.
    
    Args:
        file_path: Path to JSON file
        max_size: Maximum file size in bytes (default 10MB)
        
    Returns:
        Parsed JSON data
        
    Raises:
        SecurityError: If file is too large or contains dangerous content
        ValueError: If JSON is invalid
    """
    # Validate path
    safe_path = sanitize_path(file_path)
    
    # Check file size
    size = os.path.getsize(safe_path)
    if size > max_size:
        raise SecurityError(f"File too large: {size} bytes (max {max_size})")
    
    # Load and parse
    with open(safe_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Basic check for embedded code (simple heuristic)
    dangerous_patterns = ['__import__', 'eval(', 'exec(', 'compile(', '__builtins__']
    for pattern in dangerous_patterns:
        if pattern in content:
            raise SecurityError(f"Potentially dangerous content detected: {pattern}")
    
    return json.loads(content)


def safe_json_save(data: Any, file_path: str) -> None:
    """
    Safely save data to JSON file.
    
    Args:
        data: Data to serialize
        file_path: Target file path
    """
    # Validate path
    safe_path = sanitize_path(file_path)
    
    # Ensure directory exists
    dir_path = os.path.dirname(safe_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    # Atomic write (write to temp file, then rename)
    temp_path = safe_path + '.tmp'
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, safe_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def mask_sensitive_data(text: str, mask: str = '***') -> str:
    """
    Mask sensitive data like API keys in logs/error messages.
    
    Args:
        text: Text that might contain sensitive data
        mask: Mask string to use
        
    Returns:
        Masked text
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Mask common API key patterns
    patterns = [
        (r'[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}["\']?', f'API_KEY={mask}'),
        (r'[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}["\']?', f'TOKEN={mask}'),
        (r'[Ss][Ee][Cc][Rr][Ee][Tt]\s*[:=]\s*["\']?[a-zA-Z0-9_-]{20,}["\']?', f'SECRET={mask}'),
        (r'key=[a-zA-Z0-9_-]{20,}', f'key={mask}'),
        (r'token=[a-zA-Z0-9_-]{20,}', f'token={mask}'),
        (r'Authorization:\s*[Bb]earer\s+[a-zA-Z0-9_-]+', f'Authorization: Bearer {mask}'),
    ]
    
    import re
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    
    return text


def validate_enum(value: str, allowed_values: List[str]) -> str:
    """
    Validate that a value is one of the allowed enum values.
    
    Args:
        value: Value to validate
        allowed_values: List of allowed values
        
    Returns:
        Validated value
        
    Raises:
        InputValidationError: If value not in allowed list
    """
    if value not in allowed_values:
        raise InputValidationError(f"Invalid value '{value}'. Allowed: {', '.join(allowed_values)}")
    return value


def secure_subprocess_run(cmd: List[str], **kwargs) -> Any:
    """
    Wrapper for subprocess.run with security defaults.
    
    Args:
        cmd: Command as list of arguments (NEVER use shell=True)
        **kwargs: Additional arguments for subprocess.run
        
    Returns:
        CompletedProcess instance
        
    Raises:
        SecurityError: If shell=True is attempted
    """
    # SECURITY: Never allow shell=True
    if kwargs.get('shell'):
        raise SecurityError("shell=True is not allowed for security reasons")
    
    # Set secure defaults
    kwargs.setdefault('capture_output', True)
    kwargs.setdefault('text', True)
    kwargs.setdefault('timeout', 300)  # 5 minute default timeout
    
    import subprocess
    return subprocess.run(cmd, **kwargs)


# Export all security functions
__all__ = [
    'SecurityError',
    'PathTraversalError', 
    'InputValidationError',
    'sanitize_path',
    'validate_filename',
    'validate_topic',
    'safe_json_load',
    'safe_json_save',
    'mask_sensitive_data',
    'validate_enum',
    'secure_subprocess_run',
]

# Security Policy

## Reporting a Vulnerability

**Please do not open public issues for security vulnerabilities.**

If you discover a security vulnerability, please email **security@your-org.com** with:

1. **Description**: What is the vulnerability?
2. **Location**: File path and line number (if applicable)
3. **Reproduction**: Steps to reproduce
4. **Impact**: Severity and potential impact
5. **Fix suggestion**: If you have one

We will:
- Acknowledge receipt within 48 hours
- Assess severity
- Develop and test a fix
- Release a patched version
- Credit you in the release (unless you prefer anonymity)

## Security Best Practices

### For Users

1. **Keep dependencies updated**
   ```bash
   pip install --upgrade torch transformers pipecat-ai
   ```

2. **Secure API keys**
   - Never commit `.env` with real tokens
   - Use `.env.local` for local overrides
   - Set strong HuggingFace tokens in secure storage

3. **CUDA Security**
   - Run on trusted networks only
   - Use TLS/HTTPS in production
   - Validate input lengths

4. **Container Security**
   - Run containers as non-root when possible
   - Use specific image versions (not `latest`)
   - Scan images for vulnerabilities
   ```bash
   docker scan qwen-markel-tts:latest
   ```

### For Developers

1. **Code Review**
   - All code changes require review
   - Pay attention to external input handling
   - Check for secrets in code

2. **Dependency Management**
   - Regularly update dependencies
   - Use dependency scanners
   - Lock versions in production

3. **Testing**
   - Test security-critical code paths
   - Include input validation tests
   - Test error handling

4. **Secrets Management**
   - Never log sensitive data
   - Use `.env` for configuration
   - Rotate tokens regularly

## Known Security Considerations

### Input Validation
- Maximum text length: 1,000 characters per request
- Server validates all JSON inputs
- Malformed requests return 400 Bad Request

### Memory Safety
- PyTorch/CUDA handles memory management
- No buffer overflows possible in Python layer
- GPU memory is isolated per process

### CUDA Kernel Considerations
- Original AlpinDale kernel designed for RTX 5090
- No known vulnerabilities in kernel
- Kernel runs in secure GPU context

### API Security
- Current implementation: **no authentication**
- Suitable for: Local/trusted network use
- Production: Add authentication layer (OAuth, API keys, TLS)

## Security Checklist for Production

- [ ] Enable HTTPS/TLS
- [ ] Add API authentication (OAuth/API keys)
- [ ] Rate limiting enabled
- [ ] Input validation enforced
- [ ] Secrets stored securely (not in code)
- [ ] Logging sanitized (no tokens)
- [ ] Firewall rules configured
- [ ] Regular dependency updates
- [ ] Security headers set (CORS, CSP)
- [ ] Error messages don't leak info

## Compliance

This project does not currently support:
- HIPAA compliance (medical data)
- GDPR compliance (EU privacy regulations)
- SOC 2 certification
- PCI DSS (payment data)

For these use cases, additional security measures are required.

## Security Updates Policy

- **Critical**: Released ASAP (emergency patch)
- **High**: Released within 1 week
- **Medium**: Released within 1 month
- **Low**: Bundled in next release

## Third-Party Dependencies

See [pyproject.toml](pyproject.toml) for current dependencies.

Major dependencies:
- **PyTorch**: Security updates tracked via [pytorch.org/security](https://pytorch.org/security)
- **Transformers**: Updates via [huggingface.co](https://huggingface.co)
- **FastAPI**: Updates via [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **CUDA**: Updates via [nvidia.com](https://nvidia.com)

## Version Support

| Version | Supported | EOL Date |
|---------|-----------|----------|
| 0.1.x | ✓ Yes | TBD |
| < 0.1 | ✗ No | 2026-05-15 |

We support the latest version only. Upgrade regularly for security fixes.

## Questions?

For security questions (non-vulnerability), please:
1. Check [DOCUMENTATION.md](DOCUMENTATION.md)
2. Open a GitHub Discussion
3. Email **security-questions@your-org.com**

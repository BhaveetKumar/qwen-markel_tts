# Contributing to qwen-markel-tts

Thank you for your interest in contributing! This document provides guidelines for development.

## Setting Up Development Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests to verify setup
pytest tests/ -v
```

## Development Workflow

### 1. Code Style

We use **black** and **isort** for code formatting.

```bash
# Format code
make format

# Check formatting
make lint
```

### 2. Testing

Run tests before committing:

```bash
# Run all tests
make test

# Run quick tests
make test-quick

# Watch mode (requires pytest-watch)
make watch-test
```

**Test Coverage**: Aim for > 80% on new code.

### 3. Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
make test

# Commit with clear message
git commit -m "Add feature: clear description"

# Push and create pull request
git push origin feature/your-feature-name
```

### 4. Code Review Checklist

Before submitting a PR:

- [ ] Tests pass locally (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] No linting issues (`make lint`)
- [ ] Docstrings added to public APIs
- [ ] Type hints included
- [ ] Changelog updated (if applicable)

## Common Development Tasks

### Adding a New Feature

1. Create feature branch: `git checkout -b feature/my-feature`
2. Add tests in `tests/test_my_feature.py`
3. Implement in `src/module/feature.py`
4. Update docs if needed
5. Run `make test && make lint`
6. Commit and push

### Modifying the Kernel

See [docs/KERNEL_CHANGES.md](docs/KERNEL_CHANGES.md) for detailed kernel integration notes.

To test kernel modifications:

```bash
make build  # Recompile CUDA extension
make test   # Run tests
make benchmark  # Benchmark changes
```

### Running Server Locally

```bash
# Start server
make run

# In another terminal, test it
curl http://localhost:8000/health

# Run CLI
make cli TEXT="Your text here"

# Generate samples
make cli-samples
```

### Debugging

Run server with verbose logging:

```bash
bash scripts/run_server.sh  # Already logs to stdout
```

Use Python debugger in code:

```python
import pdb; pdb.set_trace()  # Breakpoint
```

## Project Structure

```
src/
├── megakernel/        # Kernel adapter
├── qwen3_tts/         # Model loading & decoding
├── server/            # FastAPI server
└── pipecat_adapter/   # Pipecat integration

tests/
└── test_*.py          # Unit tests (no GPU required)

scripts/
├── build.sh           # CUDA build
├── run_server.sh      # Start server
├── benchmark.py       # Performance tests
├── cli.py             # Command-line tool
├── demo.py            # Pipecat demo
└── generate_samples.py # Sample generation
```

## Documentation

### Adding Documentation

1. Update relevant `.md` files in root or `docs/`
2. Cross-reference with links: `[link text](path/to/file.md)`
3. Include code examples where helpful
4. Use consistent formatting

### Documentation Standards

- Use clear headings hierarchy
- Include code examples
- Add tables for reference data
- Link to related docs

## Performance and Optimization

### Benchmarking

```bash
# Run benchmark
make benchmark

# Run extended benchmark (30 runs)
make benchmark-long

# Compare results
python scripts/benchmark.py --runs 30 --json > results.json
```

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... code to profile ...
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

## Reporting Issues

When reporting issues, include:

1. **Environment**: Python version, CUDA version, GPU model
2. **Reproduction steps**: Minimal code to reproduce
3. **Error traceback**: Full error message
4. **Expected vs actual**: What should happen vs what happens

Example issue:

```
**Title**: Server crashes on RTX 3080

**Environment**:
- Python 3.11
- CUDA 12.1
- RTX 3080

**Reproduction**:
1. `pip install -e .`
2. `bash scripts/run_server.sh`
3. `curl -X POST http://localhost:8000/tts/stream ...`

**Error**:
```
RuntimeError: CUDA out of memory
```

**Expected**: Streaming response with 96 tokens
```

## Submitting a Pull Request

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Document** changes
6. **Submit** PR with clear description

### PR Description Template

```
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe testing procedure

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
- [ ] No breaking changes

## Screenshots/Benchmarks
If applicable, add performance comparison
```

## Code Standards

### Type Hints

All public functions should have type hints:

```python
def synthesize(
    text: str,
    temperature: float = 0.7,
) -> bytes:
    """Synthesize text to speech."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def process(data: list[int]) -> dict[str, float]:
    """
    Process data and return statistics.
    
    Args:
        data: Input list of integers.
    
    Returns:
        Dictionary with mean, std, min, max.
    
    Raises:
        ValueError: If data is empty.
    
    Example:
        >>> result = process([1, 2, 3])
        >>> result['mean']
        2.0
    """
```

### Logging

Use `loguru` for logging:

```python
from loguru import logger

logger.info("Server started on port 8000")
logger.warning("Model load slow on first run")
logger.error("CUDA device error: {}", error_msg)
```

## Release Process

1. Update version in `pyproject.toml`
2. Update [CHANGELOG.md](CHANGELOG.md) (when created)
3. Tag release: `git tag v0.2.0`
4. Push tags: `git push origin --tags`

## Getting Help

- **Documentation**: See [DOCUMENTATION.md](DOCUMENTATION.md)
- **Issues**: Check [GitHub Issues](https://github.com/your-org/qwen-markel_tts/issues)
- **Discussions**: Use GitHub Discussions for questions

## License

By contributing, you agree to license your contributions under the same terms as the project.

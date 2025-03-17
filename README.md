[![CI](https://github.com/PandABlocks-ioc/fastcs-PandABlocks/actions/workflows/ci.yml/badge.svg)](https://github.com/PandABlocks-ioc/fastcs-PandABlocks/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/PandABlocks-ioc/fastcs-PandABlocks/branch/main/graph/badge.svg)](https://codecov.io/gh/PandABlocks-ioc/fastcs-PandABlocks)
[![PyPI](https://img.shields.io/pypi/v/fastcs-pandablocks.svg)](https://pypi.org/project/fastcs-pandablocks)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcs_pandablocks

A softioc to control a PandABlocks-FPGA using [PandABlocks-client](https://github.com/PandABlocks/PandABlocks-client).

Source          | <https://github.com/PandABlocks-ioc/fastcs-PandABlocks>
:---:           | :---:
PyPI            | `pip install fastcs-pandablocks`
Docker          | `docker run ghcr.io/pandablocks-ioc/fastcs-PandABlocks:latest`
Documentation   | <https://pandablocks-ioc.github.io/fastcs-PandABlocks>
Releases        | <https://github.com/PandABlocks-ioc/fastcs-PandABlocks/releases>

<!-- README only content. Anything below this line won't be included in index.md -->

Start the ioc with the project script `fastcs-pandablocks`:

```
fastcs-pandablocks run <hostname> <prefix> --screens-dir ./screens --log-level INFO --poll-period 0.1
```

See <https://pandablocks-ioc.github.io/fastcs-PandABlocks> for more detailed documentation.

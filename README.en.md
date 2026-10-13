# AuraLinc Community

[日本語](./README.md)

Community site for AuraLinc. AuraLinc EcoCONNECT is published as open source.

## Site sections

| Section | Contents |
| --- | --- |
| **Docs** | Getting started, tutorials, repo map, FAQ |
| **Workshop materials** | Materials for workshops |
| **Community plaza** | Ideas, questions, and suggestions (GitHub Discussions / giscus) |

- **Site:** https://hollyrock.github.io/AuraLinc-Community/
- **Discussions:** https://github.com/hollyrock/AuraLinc-Community/discussions

```text
AuraLinc-Community/
├── docs/                   # Source for GitHub Pages
│   ├── index.md
│   ├── community/          # Ideas, questions, suggestions
│   ├── docs/               # Manuals, FAQ, and related docs
│   ├── en/                 # English pages
│   ├── public/             # Logo and shared assets
│   └── steam/              # Workshop materials
├── firmware/
│   ├── EcoCONNECT/         # EcoCONNECT control code
│   └── pico2/
│       ├── release/        # Pico 2 image
│       └── src/            # Pico 2 firmware code
├── hardware/
│   ├── main-board/         # Main-board circuit data
│   │   └── libs/           # KiCad libraries
│   └── steam-board/        # STEAM sensor-board circuit data
│       └── libs/           # KiCad libraries
└── site/                   # Built site
```

## Licenses

This project uses a different license for each component.

- **Hardware design** (`/hardware/`): [CERN-OHL-P-2.0](hardware/LICENSE-CERN-OHL-P.txt)
- **Firmware source code** (`/firmware/`): [MIT License](firmware/LICENSE-MIT.txt)
- **Documentation and media** (`/docs/`): [CC-BY-4.0](docs/LICENSE-CC-BY.txt)

See the `LICENSE` file in each folder.

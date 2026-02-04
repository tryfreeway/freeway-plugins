# Freeway Plugins

Freeway is an on-device speech-to-text app for macOS.
Plugins allow you to modify the result using third-party services, and even control your Mac by launching other apps or services.

This repository contains community plugins that extend Freeway with custom automations, AI enhancements, formatting helpers, and more.

## Getting Started

Visit https://docs.tryfreeway.com to get started with the Freeway API and plugin system.
If you want to discover, install, or manage plugins locally, follow the plugin section in the documentation for instructions specific to your version of Freeway.

Be sure to read and follow our Plugin Guidelines before submitting a new plugin or interacting with others in this repository.

## What You Can Build

Freeway plugins are small (or not) Python scripts that run on your transcribed text or react to specific voice patterns.
They can, for example:

- Post-process audio.
- Post-process text (cleanup, formatting, templates, signatures).
- Call local or remote AI models.
- Automate workflows by transforming or routing dictated text.

Each plugin lives in its own folder and declares how it integrates with Freeway (triggers, configuration, outputs).

## Repository Structure

This repository is organized around individual plugins:
- `plugins/` – root folder containing all public plugins.
- `plugins/<plugin-name>/` – one plugin per folder, with its own code and metadata.
- `INDEX.json` – contains all plugins that are available in the Plugins Library inside the app.

Check existing plugins and examples to understand recommended structure, style, and patterns.

## Creating a Plugin

To create your own plugin:

1. Create a new folder under `plugins/` with a unique, descriptive name (e.g. `smart-way`).
2. Add the required meta.json file that describes your plugin (name, description, author, version, compatibility, any settings).
3. Implement the plugin logic in Python using the Freeway plugin API.
4. Test your plugin locally in Freeway until it behaves as expected.
5. Optionally add a short `README.md` inside your plugin folder that explains how to test it or any other notes.

If you are starting from scratch, copy one of the example plugins and adapt it instead of reinventing the structure.

## Plugin Guidelines

To keep the ecosystem healthy and predictable, please follow these rules when publishing a plugin here:

- Keep the scope focused and understandable at a glance.
- Prefer minimal, well-documented code over complex, tightly coupled logic.
- Avoid hard-coding user‑specific paths, secrets, or credentials, use configuration instead.
- Be explicit and transparent about any external network calls (APIs, cloud models, telemetry).
- Respect privacy: don't log or transmit user content unless it is clearly documented and necessary.
- Include a clear license for your plugin (MIT by default if not specified otherwise).

We may ask you to adjust your plugin if it conflicts with these guidelines.

## Contributing

We welcome contributions in the form of new plugins, improvements to existing ones, and documentation updates.

To submit a plugin:

1. Fork this repository.
2. Create a new branch for your work:
   ```bash
   git checkout -b my-awesome-plugin
   ```
3. Add your plugin under `plugins/<plugin-name>/` following the structure and guidelines above.
4. Ensure your plugin loads and runs correctly in Freeway and passes any existing checks or linters.
5. Open a pull request against the `main` branch with:
   - A concise title (e.g. `Add smart-way plugin`).
   - A brief description of what the plugin does and how it is used.
   - Links or screenshots/GIFs are welcome but optional.

We review pull requests for functionality, safety, code quality, and documentation clarity.
If a plugin is experimental, incomplete, or unclear, we may request changes or decide not to merge it.

## Feedback

Freeway plugins are most useful when shaped by real workflows and feedback.
If you have ideas on how to improve the plugin system, APIs, or developer experience, please open an issue in this repository
or [contact us](https://tryfreeway.com/contact).
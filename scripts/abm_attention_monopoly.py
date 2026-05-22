from __future__ import annotations

from io_klems_attention import ABM_PATH, CONFIG_PATH, load_config, bass_path


def main() -> None:
    config = load_config(CONFIG_PATH)
    paths = bass_path(config)
    paths.to_csv(ABM_PATH, index=False)
    print(f"Saved ABM paths: {ABM_PATH}")


if __name__ == "__main__":
    main()

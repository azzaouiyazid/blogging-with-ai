# Convenience Makefile

.PHONY: setup ui

setup:
	bash scripts/setup_local.sh

ui:
	streamlit run tools/setup_ui.py

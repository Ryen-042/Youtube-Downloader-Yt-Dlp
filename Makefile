.PHONY: run install install-reqs clean ruff flake8 lint update-modules probe

.DEFAULT_GOAL := run

# For some reason, the globstar (eg, **/*.py) is broken in windows. This is a workaround.
# Source: https://stackoverflow.com/questions/2483182/recursive-wildcards-in-gnu-make
# Other: https://dev.to/blikoor/customize-git-bash-shell-498l
rwildcard=$(foreach d,$(wildcard $(1:=/*)),$(call rwildcard,$d,$2) $(filter $(subst *,%,$2),$d))

run:
	@echo "Running..."
	python youpy/main.py
	@echo "Done."

install:
	@echo "Installing package from local files..."
	pip uninstall youpy -y
	pip install .
	@echo "Done."

install-reqs: requirements.txt
	@echo "Installing requirements..."
	pip install --upgrade -r requirements.txt
	@echo "Done."

clean:
	@echo "Removing the build related directories..."
	rm -rf build dist youpy.egg-info
	rm -rf $(call rwildcard,.,*__pycache__)
	@echo "Done."

ruff:
	@echo "Linting Python files..."
	ruff .
	@echo "Done."

flake8:
	@echo "Linting Python files..."
	flake8 --color always
	@echo "Done."

lint: ruff flake8

update-modules:
	@echo "Updating the modules..."
	pip install --upgrade yt-dlp yt-dlp-ejs
	@echo "Done."


probe:
	ffprobe ; <filename>
file := depmanager/common/version_var.py
var_file := $(shell cat ${file})
var_version = $(addsuffix $(subst .,_,$(subst VAR = ,,$(var_file))),dependency_manager_)

reqs:
	pip3 install pyinstaller
	pip3 install -r requirements.txt

activate:
	source ./venv/Scripts/activate

black:
	python -m isort --sl --line-length 120 depmanager
	python -m black --line-length 120 depmanager

lint:
	python -m isort --sl --line-length 120 depmanager
	python -m black --line-length 120 depmanager
	python -m pylint depmanager

build:
	pyinstaller \
		--onefile \
		--name $(var_version) \
		--add-data "depmanager/resources/morph.jpg;." \
		--add-data "depmanager/resources/plugin.jpg;." \
		--add-data "depmanager/resources/sound.jpg;." \
		--add-data "depmanager/resources/unity.jpg;." \
		depmanager/run_var.py
	#find . -name "$(var_version).spec" -exec rm {} \;
	rm -rf build/$(var_version)

clean:
	find . -name "*.spec" -exec rm {} \;
	rm -rf build
	rm -rf dist
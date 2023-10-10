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

build-full:
	find . -name "*.spec" -exec rm {} \;
	rm -rf build
	rm -rf dist
	pyinstaller \
	    --clean -y --dist ./dist/windows \
		--onefile \
		--name dependency_manager \
		--add-data "depmanager/resources/morph.jpg;." \
		--add-data "depmanager/resources/plugin.jpg;." \
		--add-data "depmanager/resources/sound.jpg;." \
		--add-data "depmanager/resources/unity.jpg;." \
		depmanager/run_var.py

build-quick:
	pyinstaller --clean -y --dist ./dist/windows ./dependency_manager.spec

authorize:
	ssh-add ~/.ssh/id_ed25519_phroz3ncode

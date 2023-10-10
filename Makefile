reqs:
	python -m pip install --upgrade pip
	pip3 install -r requirements.txt

activate:
	source ../virtualenvs/dependency_manager_311/Scripts/activate

activate_310:
	source ../virtualenvs/dependency_manager_310/Scripts/activate

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
	    --dist ./dist/windows \
		--onefile \
		--name dependency_manager \
		--add-data "depmanager/resources/morph.jpg;." \
		--add-data "depmanager/resources/plugin.jpg;." \
		--add-data "depmanager/resources/sound.jpg;." \
		--add-data "depmanager/resources/unity.jpg;." \
		depmanager/run_var.py

build-quick:
	pyinstaller --dist ./dist/windows ./dependency_manager.spec

authorize:
	ssh-add ~/.ssh/id_ed25519_phroz3ncode

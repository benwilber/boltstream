REGION ?= nyc3
ENV ?= dev
LIMIT ?= $(REGION)-$(ENV)-boltstream-me
TAGS ?= all
PYCURL_SSL_LIBRARY ?= openssl
OPENSSL_PREFIX ?= $(shell brew --prefix openssl)
LDFLAGS ?= "-L$(OPENSSL_PREFIX)/lib"
CPPFLAGS ?= "-I$(OPENSSL_PREFIX)/include"

venv:
	python3 -m venv venv

deps:
	python -m pip install --upgrade pip wheel
	PYCURL_SSL_LIBRARY=$(PYCURL_SSL_LIBRARY) \
	LDFLAGS=$(LDFLAGS) CPPFLAGS=$(CPPFLAGS) \
		python -m pip install --requirement=requirements.txt

freeze:
	python -m pip freeze > requirements.txt

migrate:
	./manage.py migrate --noinput

migrations:
	./manage.py makemigrations

statics:
	./manage.py collectstatic --noinput

test:
	./manage.py test

dumpinitialdata:
	./manage.py dumpdata --natural-foreign --natural-primary \
		--exclude=admin.logentry --all --indent=2 > boltstream/fixtures/initial_data.json

loadinitialdata:
	./manage.py loaddata initial_data

dumptestdata:
	./manage.py dumpdata --natural-foreign --natural-primary \
		--exclude=admin.logentry --all --indent=2 > boltstream/fixtures/tests.json

loadtestdata:
	./manage.py loaddata tests

coverage:
	coverage run ./manage.py test
	coverage html --include=boltstream/*

lint:
	flake8 boltstream
	black --check boltstream

format:
	isort --atomic boltstream
	black boltstream

clean:
	rm -rf venv media static db.sqlite3 staticfiles.json
	$(MAKE) venv
	mkdir media
	sh -c "./bin/boot $(MAKE) deps migrate loadinitialdata statics"

cleandb:
	rm -f db.sqlite3
	$(MAKE) migrate loadinitialdata

run:
	./manage.py runserver

shell:
	./manage.py shell

deploy:
	ANSIBLE_CONFIG=ansible/ansible.cfg \
		ansible-playbook \
			--inventory=ansible/digital_ocean.py --tags="$(TAGS)" \
			--limit="$(LIMIT)" --extra-vars="region=$(REGION) env=$(ENV)" ansible/site.yml

restart:
	ANSIBLE_CONFIG=ansible/ansible.cfg \
		ansible "$(LIMIT)" --inventory=ansible/digital_ocean.py \
			--module-name=service --args="name=$(NAME) state=restarted"

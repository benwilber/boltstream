REGION ?= nyc3
ENV ?= dev

init:
	terraform init

refresh:
	terraform refresh -var region=$(REGION) -var env=$(ENV) -state states/$(REGION)-$(ENV).tfstate

plan:
	terraform plan -var region=$(REGION) -var env=$(ENV) -state states/$(REGION)-$(ENV).tfstate

apply:
	terraform apply -var region=$(REGION) -var env=$(ENV) -state states/$(REGION)-$(ENV).tfstate

destroy:
	terraform destroy -var region=$(REGION) -var env=$(ENV) -state states/$(REGION)-$(ENV).tfstate

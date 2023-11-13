# WIP - High level notes for setup


## Step 1 Create Synthetic Funtions

% python dfaastest/funktion_generator.py --action create --funk-name decompress


## Step 2 Create Database and setup DB config

Create a DB as defined in the SQL file:

- sql/create_ddl.sql

Setup the DB connection credentials configuration in the `config.yaml` file, section `database`.

## Step 3 Install CMAB Agent


## Step 4 Install Logs Processor


## Step 5 Install the Synthetic Functions

The following command will install the `decompress` function:

```
% python dfaastest/funktion_generator.py --action create --funk-name decompress
```

## Step 6 Start the operator

The following command will operate the decompress function:

% python dfaastest/operator.py --action run --funk-name decompress

## Step 7 Generate Load

The following command will generate load for the decompress function:

% python dfaastest/gen_load.py --action test --funk-name decompress 



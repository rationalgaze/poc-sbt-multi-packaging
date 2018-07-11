#!/usr/bin/env bash

# Récupération des paramètres
user=$1
realm=$2
master=$3
deploy_mode=$4
spark_opts=$5
jar=$6
class=$7
args=${@:8} # liste des parametres

# Kinit
kinit ${user}@${realm} -k -t ${user}.keytab

# Lancement du job
spark2-submit --master ${master} --deploy-mode ${deploy_mode} ${spark_opts} --class ${class} ${jar} ${args}
if [ $? -eq 1 ]; then
    echo "[ERROR]: Spark2-submit FAIL"
    exit 1
fi
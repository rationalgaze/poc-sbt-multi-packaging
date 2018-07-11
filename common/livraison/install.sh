#!/bin/sh

# Installe les sources et lance les coordinateurs Oozie
# Pour demarrer les coordinateurs (sauf coord jobs2) a 14h (pas reel 9h):
# ./install.sh

ORANGE_VERSION_GOROCO=$1
URL_OOZIE="http://opxlrcli02.netxlr8.orange.fr:12000"
DIR_BASE=/user/otarie
HDFS_INSTALL_DIR=/user/otarie/installation
LOCAL_INSTALL_DIR=wqrt5363_install
LIVRABLES_DIR=${LOCAL_INSTALL_DIR}/"PA-OTA-ETL-"${ORANGE_VERSION_GOROCO}

################################
#                              #
#      Installing sources      #
#                              #
################################

# Kerberos authentication
kinit otarie@NETXLR8.FR -k -t otarie.keytab

# Delete same version if already exists
hdfs dfs -rm -r -f -skipTrash ${DIR_BASE}/${ORANGE_VERSION_GOROCO}

# Extraction de l'archive
rm -rf ${LOCAL_INSTALL_DIR}
mkdir -p ${LOCAL_INSTALL_DIR}
hdfs dfs -get ${HDFS_INSTALL_DIR}/*${ORANGE_VERSION_GOROCO}*.tar ${LOCAL_INSTALL_DIR}
tar -xf ${LOCAL_INSTALL_DIR}/*.tar -C ${LOCAL_INSTALL_DIR}

# Put source on hdfs
hdfs dfs -mkdir -p ${DIR_BASE}/${ORANGE_VERSION_GOROCO} ${DIR_BASE}/current
hdfs dfs -put ${LIVRABLES_DIR}/* ${DIR_BASE}/${ORANGE_VERSION_GOROCO}

# Set current = current.old
hdfs dfs -rm -r -f -skipTrash ${DIR_BASE}/current.old
hdfs dfs -mv ${DIR_BASE}/current ${DIR_BASE}/current.old

# Set new = current
hdfs dfs -cp ${DIR_BASE}/${ORANGE_VERSION_GOROCO} ${DIR_BASE}/current

# Copy additional resources (heavy .jar ...)
hdfs dfs -cp ${DIR_BASE}/installation/JDBCQuery.jar  ${DIR_BASE}/current/libs
hdfs dfs -cp ${DIR_BASE}/installation/libudfaltran.so  ${DIR_BASE}/current/libs

#############################################
#  Mettre a jour les droits du dossier HDFS de livraison
#    - Dossiers: chmod 775
#    - Fichiers: chmod 664
#############################################

TARGET=${DIR_BASE}/current

hdfs dfs -ls -R ${TARGET} | grep '^d' | awk '{print $8}' | xargs -P 1 hdfs dfs -chmod 770
hdfs dfs -ls -R ${TARGET} | grep -v '^d' | awk '{print $8}' | xargs -P 1 hdfs dfs -chmod 660

# Droit particuliers: dossier current et libs, hébergeant les UDF Impala
hdfs dfs -chmod 771 ${TARGET}
hdfs dfs -chmod 775 ${TARGET}/libs
hdfs dfs -chmod 665 ${TARGET}/libs/com.altran.jar
hdfs dfs -chmod 665 ${TARGET}/libs/libudfaltran.so

cd ${LIVRABLES_DIR}
rm -rf ${LOCAL_INSTALL_DIR}
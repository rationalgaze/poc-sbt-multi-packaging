#!/usr/bin/env python
# -*- coding: utf-8 -*-

#####################################################
#                                                   #
# create_deliverable.py créé une archive contenant  #
#  - les sources otarie_etl                         #
#  - les configurations de l'environnement ciblé    #
#                                                   #
#####################################################

from __future__ import unicode_literals

import fnmatch
import tarfile
from ConfigParser import ConfigParser
from argparse import ArgumentParser
from contextlib import closing
from lxml.etree import Element, SubElement, XMLParser, parse
from os import listdir, makedirs, walk
from os.path import basename, dirname, exists, isfile, isdir, join, realpath
from shutil import copy, copytree, rmtree
from sys import exit

#####################################################
#                                                   #
# Constantes, arguments, variables globales         #
#                                                   #
#####################################################

# Environnement de déploiement possible
ENVIRONMENTS = ["qualification", "production"]

# Chemin du dossier racine otarie_etl
ROOT = dirname(dirname(realpath(__file__)))

DIR_LIBS = join(ROOT, "build")
DIR_OOZIE = join(ROOT, "oozie")
DIR_CONFIG = join(ROOT, "config")

# Eléments (dossiers, fichiers) à exporter lors de la construction de l'archive
SOURCE_FILES = [DIR_LIBS, DIR_OOZIE, DIR_CONFIG]

# Nommage de l'archive/version
VERSION_PREFIX = "SUP"
ARCHIVE_PREFIX = "-".join(["PA", VERSION_PREFIX])

# Nom donné à la balise credentials dans les workflows Oozie
# Réutilisé par les actions Oozie ayant besoin d'un accès à Hive
CREDENTIALS_HIVE_NAME = "hive_credentials"


# Autres paramètres globaux et arguments: initialisés à l'exécution (voir parse_args()


#####################################################
#                                                   #
# Fonctions                                         #
#                                                   #
#####################################################

# Gestion des arguments en entrée de script
def parse_args():
    ###################
    # Arguments globaux
    ###################
    global ENV
    global VERSION
    global OUTPUT

    # Chemin du Sous-dossier "tmp" du dossier de sortie: sert à construire l'archive
    global OUTPUT_TMP
    global CLEAN_TMP
    # Chemin du dossier de configuration spécifique à l'environnement ciblé, mis à jour après parsing des arguments
    global DIR_CONFIG_ENV
    global CONFIG
    # Nom de l'archive finale
    global ARCHIVE_NAME

    # Arguments du programmes
    parser = ArgumentParser(description="Génère un livrable des sources Otarie")
    parser.add_argument("-e", "--environment",
                        dest="env",
                        help="Environnement de déploiement: {}".format(", ".join(ENVIRONMENTS)))
    parser.add_argument("-v", "--version",
                        dest="version",
                        help="Version  'G0R0C0' du livrable")
    parser.add_argument("-o", "--output_dir",
                        dest="output_dir",
                        help="Dossier de sortie du livrable (chemin relatif)")
    parser.add_argument("--noclean",
                        dest="noclean",
                        action="store_true",
                        default=False,
                        help="Non-suppression du dossier de travail temporaire en fin de script")
    opts = parser.parse_args()

    # Gestion erreur et stockage arguments
    if opts.env not in ENVIRONMENTS:
        print("--environment obligatoire, attendu: " + ", ".join(ENVIRONMENTS))
        parser.print_help()
        exit(1)
    else:
        # Lecture du fichier de configuration
        ENV = opts.env
        DIR_CONFIG_ENV = join(DIR_CONFIG, ENV)
        CONFIG = ConfigParser()
        CONFIG.read(join(DIR_CONFIG_ENV, "config"))

    if opts.version is None:
        print("--version obligatoire")
        parser.print_help()
        exit(1)
    else:
        VERSION = opts.version
        ARCHIVE_NAME = "{}-{}".format(ARCHIVE_PREFIX, VERSION)

    if opts.output_dir is None or opts.output_dir in SOURCE_FILES:
        print("--output obligatoire, ne doit pas déjà éxister")
        parser.print_help()
        exit(1)
    else:
        OUTPUT = join(ROOT, opts.output_dir)
        OUTPUT_TMP = join(OUTPUT, ARCHIVE_NAME)

    CLEAN_TMP = not opts.noclean


# Suppression d'un dossier
def remove_dir(src_dir):
    if exists(src_dir):
        print("[Suppression] {}".format(src_dir))
        rmtree(src_dir)


# Copie d'un élément, dossier ou fichier
def copy_element(src_path, dest_path):
    if isfile(src_path):
        copy_file(src_path, dest_path)
    elif isdir(src_path):
        copy_dir(src_path, dest_path)


# Copie d'un dossier vers un dossier
def copy_dir(src_path, dest_path):
    print("[Copie] {} -> {}".format(src_path, dest_path))
    copytree(src_path, dest_path)


# Copie des fichiers dont le nom match une regex
def copy_file(src_path, dest_path):
    print("[Copie] {} -> {}".format(src_path, dest_path))
    copy(src_path, dest_path)


# Ajoute un attribut credentials à un workflow en l'éditant
# Seuls les workflows utilisant une balise <hive> sont édités
def add_credentials(credentials_tuple, wf_file):
    # Parsing XML du fichier
    xml_parser = XMLParser(remove_blank_text=True)
    xml_tree = parse(wf_file, xml_parser)

    # Récupération de la balise racine
    markup_xml_root = xml_tree.getroot()

    # Si le fichier n'est pas un workflow, ne rien faire
    if "workflow-app" not in markup_xml_root.tag:
        return

    # Localisation de la balise <start>
    markup_start = markup_xml_root.xpath("//wf:start", namespaces={'wf': 'uri:oozie:workflow:0.5'})[0]

    # Récupération des balises Hive et Spark
    hive_actions = xml_tree.xpath("//h:hive2/..", namespaces={'h': 'uri:oozie:hive2-action:0.2'})
    spark_actions = xml_tree.xpath("//s:spark/..", namespaces={'s': 'uri:oozie:spark-action:0.2'})
    # Concaténation en un seul array
    must_have_cred_actions = hive_actions + spark_actions

    # Si des actions nécessitent des credentials
    if len(must_have_cred_actions) > 0:

        # Ajout d'une balise <credentials> globale au workflow
        markup_credentials = generate_credentials_markup(credentials_tuple)
        markup_start.addprevious(markup_credentials)

        # Itération sur chacune des balises à crédentialiser
        for action in must_have_cred_actions:
            # Ajout d'un attribut cred= à la balise
            print("[Credentials] Ajout pour {} -> '{}'".format(wf_file, action.get("name")))
            action.set("cred", CREDENTIALS_HIVE_NAME)

        # Sauvegarde des modifications du fichier de workflow
        xml_tree.write(wf_file, pretty_print=True, encoding="utf-8", xml_declaration=True)


# Créé un objet etree balise comme suit:
#   <credentials>
#     <credential name={credentials_name} type="hcat">
#     <property>
#       <name>hive2.server.principal</name>
#       <value>{val}</value>
#     </property>
#     <property>
#       <name>hive2.jdbc.url</name>
#       <value>{val}</value>
#     </property>
#   </credential>
# </credentials>
def generate_credentials_markup(credentials_tuple):
    # Extraction des credentials du tuple
    (uri, principal) = credentials_tuple

    markup_credentials = Element("credentials")

    markup_credential = SubElement(markup_credentials, "credential")
    markup_credential.set("name", CREDENTIALS_HIVE_NAME)
    markup_credential.set("type", "hive2")

    # Propriété hive2.server.principal
    markup_principal = SubElement(markup_credential, "property")
    markup_principal_name = SubElement(markup_principal, "name")
    markup_principal_name.text = principal[0]
    markup_principal_val = SubElement(markup_principal, "value")
    markup_principal_val.text = principal[1]

    # Propriété hive2.jdbc.url
    markup_uri = SubElement(markup_credential, "property")
    markup_uri_name = SubElement(markup_uri, "name")
    markup_uri_name.text = uri[0]
    markup_uri_val = SubElement(markup_uri, "value")
    markup_uri_val.text = uri[1]

    return markup_credentials


#####################################################
#                                                   #
# Point d'entrée                                    #
#                                                   #
#####################################################

if __name__ == '__main__':
    ################################
    # Récupération des arguments
    ################################
    parse_args()

    ################################
    # Suppression + recréation du dossier de sortie
    ################################
    remove_dir(OUTPUT)
    makedirs(OUTPUT_TMP)

    ################################
    # Création d'un fichier indiquant la version du livrable
    ################################
    with open(join(OUTPUT_TMP, "version"), "a") as version_file:
        full_version = str("-".join([VERSION_PREFIX, VERSION]))
        version_file.write(full_version)

    ################################
    # Copie des sources (pig, oozie, libs ...) dans le dossier de sortie tmp
    # - source: Job4, oozie, reader ... (voir $SOURCE_FILES)
    # - dest: $OUTPUT_TMP
    ################################
    # Pour chaque élément à exporter
    for src in SOURCE_FILES:
        # Reconstruction du chemin absolu de sortie
        dest = join(OUTPUT_TMP, basename(src))

        # Copie de l'élément, dossier ou fichier
        copy_element(src, dest)

    ################################
    # Copie des configurations spécifiques
    # - source: config/$ENV
    # - dest: $OUTPUT_TMP/libs
    ################################
    dest_libs = join(OUTPUT_TMP, basename(DIR_LIBS))
    # Pour chaque fichier de config
    for filename in listdir(DIR_CONFIG_ENV):
        # Reconstruction du chemin absolu  du fichier + copie
        src = join(DIR_CONFIG_ENV, filename)
        copy_file(src, dest_libs)

    ################################
    # Ajout des credentials aux workflows
    # Actions oozie ciblées: <hive>
    ################################
    # Récupération des credentials spécifiques à l'environnement
    (hive2_jdbc_url, hive2_server_principal) = CONFIG.items("credentials")

    # Pour chaque fichier XML
    for root, dirnames, filenames in walk(OUTPUT_TMP):
        for xml_filename in fnmatch.filter(filenames, '*.xml'):
            # Edition, si nécessaire, du workflow
            xml_filepath = join(root, xml_filename)
            add_credentials((hive2_jdbc_url, hive2_server_principal), xml_filepath)

    ################################
    # Archivage TAR
    ################################
    dest_archive = join(OUTPUT, ARCHIVE_NAME + ".tar")
    print("[Archive] Génération de {}".format(dest_archive).encode("utf-8"))
    with closing(tarfile.open(dest_archive, "w")) as archive:
        archive.add(OUTPUT_TMP, arcname=basename(OUTPUT_TMP))

    ################################
    # Nettoyage dossier tmp
    ################################
    if CLEAN_TMP:
        remove_dir(OUTPUT_TMP)

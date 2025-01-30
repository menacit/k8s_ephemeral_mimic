#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2025 Menacit AB <foss@menacit.se>
# SPDX-License-Identifier: GPL-2.0-or-later

'''k8s_ephemeral_mimic - Inject ephemeral container with mirrored environment, volumes, etc!'''

DESCRIPTION = __doc__
VERSION = '0.1'
LICENSE = 'GPL-2.0-or-later'
URL = 'https://github.com/menacit/k8s_ephemeral_mimic'
SOURCE_KEYS = ['securityContext', 'env', 'envFrom', 'volumeMounts']

# -------------------------------------------------------------------------------------------------
import logging as log
import argparse
import copy
import json
import sys

if sys.version_info < (3, 10):
    print('WARNING: This script has only been tested on Python 3.10 and later', file=sys.stderr)

# -------------------------------------------------------------------------------------------------
args = argparse.ArgumentParser(description=DESCRIPTION, epilog=f'License: {LICENSE}, URL: {URL}')

args.add_argument(
    '-i', '--input', type=argparse.FileType('rb'), default='-',
    metavar='/path/to/pod.json',
    help='Filesystem path to input pod specification in JSON format (default: stdin)')

args.add_argument(
    '-o', '--output', type=argparse.FileType('w'), default='-',
    metavar='/path/to/pod.json',
    help='Filesystem path to output pod specification patch in JSON format (default: stdout)')

args.add_argument(
    '-c', '--container', type=str,
    metavar='container-name',
    help='Name of container to mimic (required if pod contains multiple containers)')

args.add_argument(
    '-I', '--image', type=str, required=True,
    metavar='example.com/image_name:latest',
    help='Image to use in ephemeral container')

args.add_argument(
    '-e', '--env', type=str, action='append', default=[],
    metavar='FOO=BAR', dest='raw_additional_environment_variables',
    help='Additional environment variable to be set in container (may be used multiple times)')

args.add_argument(
    '-E', '--exclude', type=str, choices=SOURCE_KEYS, action='append', default=[],
    dest='exclude_keys',
    help='Exclude key from mirror of source container specification (may be used multiple times)')

args.add_argument(
    '-v', '--verbose', action='store_true', default=False,
    help='Enable verbose debug logging')

args.add_argument(
    '-V', '--version', action='version', version=VERSION,
    help='Display script version')

args = args.parse_args()

if args.verbose:
    log_level = log.DEBUG

else:
    log_level = level=log.INFO

log.basicConfig(format='%(levelname)s: %(message)s', level=log_level)
log.debug('Parsed arguments: ' + repr(args))

# -------------------------------------------------------------------------------------------------
log.debug('Reading input pod specification')

try:
    input_pod = json.load(args.input)

except Exception as error_message:
    log.critical(f'Failed to parse input pod specification as JSON: {error_message}')
    sys.exit(1)

log.debug('Performing basic sanity checking')

if not isinstance(input_pod, dict):
    log.critical('Input pod specification is not a dictionary/map')
    sys.exit(1)

if input_pod['kind'] != 'Pod' or input_pod['apiVersion'] != 'v1':
    log.critical('Input pod specification is not of kind "Pod" version 1')
    sys.exit(1)

# -------------------------------------------------------------------------------------------------
log.debug('Extracting "source container" from pod specification')

if len(input_pod['spec']['containers']) > 1:
    if not args.container:
        log.critical(
            'Input pod specification contains more than one container and argument ' +
            '"--container-name" is not supplied')

        sys.exit(1)

    source_container = None
    
    for container in input_pod['spec']['containers']:
        if container['name'] == args.container:
            log.debug('Found container matching target name in input pod specification')
            source_container = copy.deepcopy(container)
            break

    if not source_container:
        log.critical(
            'Could not find container matching target name in input pod specification: ' +
            args.container)

        sys.exit(1)

else:
    source_container = copy.deepcopy(input_pod['spec']['containers'][0])

ephemeral_container = {'targetContainerName': source_container['name'], 'image': args.image}

# -------------------------------------------------------------------------------------------------
log.debug('Parsing additionally supplied environment variables')

additional_environment_variables = []

for raw_additional_environment_variable in args.raw_additional_environment_variables:
    name, value = raw_additional_environment_variable.split('=', maxsplit=1)
    if not name or not value:
        log.critical('Environment variable is malformed: ' + raw_additional_environment_variable)
        sys.exit(1)
        
    additional_environment_variables.append({'name': name, 'value': value})

log.debug('Parsed additional environment variables: ' + repr(additional_environment_variables))

# -------------------------------------------------------------------------------------------------
log.debug('Generating name for ephemeral container')

if 'ephemeralContainers' in input_pod['spec'].keys():
    ephemeral_container['name'] = 'mimic-' + str(len(input_pod['spec']['ephemeralContainers']))

else:
    ephemeral_container['name'] = 'mimic-0'

log.debug('Generated name for ephemeral container: ' + ephemeral_container['name'])

# -------------------------------------------------------------------------------------------------
for key in SOURCE_KEYS:
    log.debug('Checking if key is defined for source container: ' + key)

    if key in args.exclude_keys:
        log.debug('Excluding key from source container: ' + key)
        continue
    
    if not key in source_container.keys():
        continue

    log.debug('Cloning key to ephemeral container: ' + key)
    ephemeral_container[key] = source_container[key]

# -------------------------------------------------------------------------------------------------
if 'env' in ephemeral_container.keys():
    log.debug('Appending "MIMIC_" prefix to sourced environment variables')

    for item in ephemeral_container['env']:
        item['name'] = 'MIMIC_' + item['name']


if 'envFrom' in ephemeral_container.keys():
    log.debug('Appending "MIMIC_" prefix to sourced "envFrom" items')
    
    for item in ephemeral_container['envFrom']:
        if 'prefix' in item.keys():
            item['prefix'] = 'MIMIC_' + item['prefix'] 

        else:
            item['prefix'] = 'MIMIC_'

if 'volumeMounts' in ephemeral_container.keys():
    log.debug('Appending "/mimic" prefix to sourced mount paths')

    for item in ephemeral_container['volumeMounts']:
        item['mountPath'] = '/mimic' + item['mountPath']

# -------------------------------------------------------------------------------------------------
if additional_environment_variables:
    log.debug('Appending additionally specified environment variables to ephemeral container')

    if 'env' in ephemeral_container.keys():
        ephemeral_container['env'].extend(additional_environment_variables)

    else:
        ephemeral_container['env'] = additional_environment_variables

# -------------------------------------------------------------------------------------------------
pod_patch = {'spec': {'ephemeralContainers': [ephemeral_container]}}
log.debug('Generated pod specification patch: ' + repr(pod_patch))

log.debug('Writing pod specification patch to output file')

try:
    json.dump(pod_patch, args.output, sort_keys=True, indent='    ')

except Exception as error_message:
    log.critical(f'Failed to write JSON patch data to output file: {error_message}')
    sys.exit(1)

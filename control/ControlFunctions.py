import subprocess
import time

import launcher

def startExperiment(message, logger):
    # TODO: Build of unikernel Image (Skript verwenden?)

    image_name = message['imageName'] # 'unikraft-1675005257' #unikraft-1674828757, unikraft-1675000514
    github_token = message['githubToken']
    operator = message['operator']

    ipAddrs = []
    sourceAddress = message['sourceAddress']
    sourcePort = message['sourcePort']
    if sourceAddress is not None and sourcePort is not None:
        ipAddrs += [f'--source-address={sourceAddress}', f'--source-port={sourcePort}']

    sinkAddress = message['sinkAddress']
    sinkPort = message['sinkPort']
    if sinkAddress is not None and sinkPort is not None:
        ipAddrs += [f'--sink-address={sinkAddress}', f'--sink-port={sinkPort}']

    controlAddress = message['controlAddress']
    controlPort = message['controlPort']
    if controlAddress is not None and controlPort is not None:
        ipAddrs += [f'--control-address={controlAddress}', f'--control-port={controlPort}']

    # deploy unikernel on google cloud
    project = 'bdspro'
    zone = 'europe-west3-a'
    image_url = f'projects/bdspro/global/images/{image_name}'

    framework, _ = launcher.get_description_from_image_name(image_name)

    image = launcher.get_image_from_family(project, framework)
    if image is None:
        logger.info(f'No image was found for family "{framework}". Building new image...')
        timestr = time.strftime('%Y%m%d-%H%M%S')
        latest_image_name = f'{framework}-{operator}-{timestr}'

        if framework == 'mirage':
            subprocess.run([f'mirage/build.sh', latest_image_name, github_token, '-t', 'virtio', f'--op={operator}'] + ipAddrs)
        else:
            subprocess.run([f'unikraft/build.sh', latest_image_name])
    else:
        latest_image_name = image.name

    image = launcher.get_image_from_url(project, image_url)
    if image is None:
        logger.info(f'Image {image_url} not found; falling back to latest image from family "{framework}".')
    else:
        latest_image_name = image.name

    image_url = f'projects/bdspro/global/images/{latest_image_name}'

    bootTime = launcher.boot_image(project, zone, framework, image_url, logger)

    # TODO: Write botTime to Firestore
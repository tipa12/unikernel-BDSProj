import launcher

def startExperiment(message, logger):
    # TODO: Build of unikernel Image (Skript verwenden?)
    image_name = 'unikraft-1674828757'

    # deploy unikernel on google cloud
    bootTime = launcher.boot_image(image_name, logger)

    # TODO: Write botTime to Firestore
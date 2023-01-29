import launcher

def startExperiment(message, logger):
    # TODO: Build of unikernel Image (Skript verwenden?)

    image_name = message['imageName'] # 'unikraft-1675005257' #unikraft-1674828757, unikraft-1675000514

    # deploy unikernel on google cloud
    bootTime = launcher.boot_image(image_name, logger)

    # TODO: Write botTime to Firestore
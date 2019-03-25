import logging
import core
import zillow
import zumper


def main():
    try:
        logging.info('Running Zillow script')
        zillow.main()
    except (KeyboardInterrupt, SystemExit) as e:
        logging.warning('Zillow script execution finished by the user')

    try:
        logging.info('Running Zumper script')
        zumper.main()
    except (KeyboardInterrupt, SystemExit) as e:
        logging.warning('Zumper script execution finished by the user')

if __name__ == '__main__':
    main()
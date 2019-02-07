from __future__ import print_function

from urllib import urlretrieve
import os, sys, json, time, errno
import requests, argparse, multiprocessing

def mkdir_p(directory):
    try:
        os.makedirs(directory)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(directory):
            pass
        else:
            raise


def get_headers(credentials):
    # Login to get access token
    response = requests.post('https://medifor.rankone.io/api/login/', {'username': credentials[0], 'password': credentials[1]})
    if response.status_code == requests.codes.ok:
        token = response.json()['key']
    else:
        print("Bad credentials!")
        sys.exit(1)

    return { "Content-Type": "application/json", "Authorization": "Token %s" % token }


def get_data(data):
    try:
        if data and not data.endswith('.json'):
            return json.loads(data)
        elif data:
            return json.loads(open(data).read().strip())
    except:
        pass

    return {}


def download(directory, url, key, headers):
    response = requests.get(url, headers=headers)
    if response.status_code != requests.codes.ok:
        return
    url = response.json()[key]
    file_name = os.path.split(url.split("?")[0])[1]
    downloadName = os.path.join(directory, file_name)

    if not os.path.exists(downloadName):
        try:
            urlretrieve(url, downloadName)
        except:
            url = url.replace("https://ceph.mediforprogram.com", "http://ceph-s3.medifor.tld:7480")
            urlretrieve(url, downloadName)


def get_camera_media(directory, hp_device_local_id, headers, download_args):
    media_url = "https://medifor.rankone.io/api/images/filters/"
    data = { "hp_device_local_id": { "type": "exact", "value": hp_device_local_id } }

    response = requests.post(media_url, headers=headers, data=json.dumps(data))
    if response.status_code != requests.codes.ok:
        return

    jsonResponse = response.json()
    if len(jsonResponse['results']) == 0:
        return

    for entry in jsonResponse['results']:
        mediaDir = "images" if entry["media_type"] == "image" else "videos" if entry["media_type"] == "video" else entry["media_type"]
        downloadDir = os.path.join(directory, "cameras", "media", mediaDir)
        download_args[1].append(download_args[0].apply_async(download, [downloadDir, entry['download'], "media", headers]))

    media_url = jsonResponse['next']
    while media_url:
        response = requests.post(media_url, headers=headers, data=json.dumps(data))
        if response.status_code != requests.codes.ok:
            return
        jsonResponse = response.json()
        if len(jsonResponse['results']) == 0:
            return

        for entry in jsonResponse['results']:
            mediaDir = "images" if entry["media_type"] == "image" else "videos" if entry["media_type"] == "video" else entry["media_type"]
            downloadDir = os.path.join(directory, "cameras", "media", mediaDir)
            download_args[1].append(download_args[0].apply_async(download, [downloadDir, entry['download'], "media", headers]))

        media_url = jsonResponse['next']


def get_from_files(metadata_file, directory, headers, download_args, **kwargs):
    try:
        infile = open(metadata_file)
    except IOError:
        print("Invalid input file!")
        return

    for line in infile:
        entry = json.loads(line.strip())
        if kwargs["subcommand"] == "media":
            mediaDir = "images" if entry["media_type"] == "image" else "videos" if entry["media_type"] == "video" else entry["media_type"]
            downloadDir = os.path.join(directory, "media", mediaDir)
            download_args[1].append(download_args[0].apply_async(download, [downloadDir, entry['download'], "media", headers]))
        elif kwargs["subcommand"] == "journals":
            download_args[1].append(download_args[0].apply_async(download, [os.path.join(directory, "journals", "archives"), entry["download"], "journal", headers]))
        else:
            download_args[1].append(download_args[0].apply_async(download, [os.path.join(directory, "cameras", "prnu"), entry["download"], "prnu", headers]))
            if "media" in kwargs.keys() and kwargs["media"]:
                get_camera_media(directory, entry["hp_device_local_id"], headers, download_args)

    infile.close()


def get_response(errs, count, total, url, data, metadata_file, directory, headers, download_args, **kwargs):
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code != requests.codes.ok:
        print(response.status_code)
        errs += 1
        time.sleep(5)
        return errs, count, url

    jsonResponse = response.json()
    if len(jsonResponse['results']) == 0:
        return errs, count, None

    errs   = 0
    url    = jsonResponse['next']
    to_add = len(jsonResponse['results']) - kwargs["resume_idx"]

    if (count + to_add) > total:
        overflow =  count + to_add - total
        index = len(jsonResponse['results']) - overflow
        count += len(jsonResponse['results'][kwargs["resume_idx"]:index])
        entries = jsonResponse['results'][kwargs["resume_idx"]:index]
    else:
        count += to_add
        entries = jsonResponse['results'][kwargs["resume_idx"]:]

    for entry in entries:
        metadata_file.write(json.dumps(entry) + "\n")
        if kwargs["subcommand"] == "media":
            mediaDir = "images" if entry["media_type"] == "image" else "videos" if entry["media_type"] == "video" else entry["media_type"]
            downloadDir = os.path.join(directory, "media", mediaDir)
            download_args[1].append(download_args[0].apply_async(download, [downloadDir, entry['download'], "media", headers]))
        elif kwargs["subcommand"] == "journals":
            download_args[1].append(download_args[0].apply_async(download, [os.path.join(directory, "journals", "archives"), entry["download"], "journal", headers]))
            download_args[1].append(download_args[0].apply_async(download, [os.path.join(directory, "journals", "probes"), entry["download"], "probes", headers]))
        else:
            download_args[1].append(download_args[0].apply_async(download, [os.path.join(directory, "cameras", "prnu"), entry["download"], "prnu", headers]))
            if "media" in kwargs.keys() and kwargs["media"]:
                get_camera_media(directory, entry["hp_device_local_id"], headers, download_args)

    return errs, count, url


if __name__ == '__main__':
    # Parse command line args
    parser = argparse.ArgumentParser(description="Filter and extract data through the MediFor API.")
    subparsers = parser.add_subparsers(dest='subcommand')

    # /api/images/
    parser_media = subparsers.add_parser("media",   help="Retrieve media metadata and files.")
    parser_media.add_argument("credentials",        help="User credentials, in format 'username:password'.")
    parser_media.add_argument("output_directory",   help="Directory to save metadata and associated files.")
    parser_media.add_argument("-l", "--limit",      help="Limit the number of records to retrieve.", type=int, default=sys.maxint)
    parser_media.add_argument("-j", "--jobs",       help="Number of download processes to spawn.", type=int)
    parser_media.add_argument("-f", "--fields",     help="Metadata fields to return, comma separated.", default=None)
    parser_media.add_argument("-d", "--data",       help="Filter data to post to the API, ex. '{\"width\": {\"type\": \"range\", \"value\": [100,200]}, \"media_type\": {\"type\": \"exact\", \"value\": \"image\"}}'.")
    parser_media.add_argument("-r", "--resume",     help="Resume a previous metadata download.  Will start at the line index of the given output file.", action="store_true", default=False)
    parser_media.add_argument("-i", "--input_file", help="Optionally download files from .json file rather than through the web API.")

    # /api/journals/
    parser_journals = subparsers.add_parser("journals", help="Retrieve journal metadata and files.")
    parser_journals.add_argument("credentials",         help="User credentials, in format 'username:password'.")
    parser_journals.add_argument("output_directory",    help="Directory to save metadata and associated files.")
    parser_journals.add_argument("-l", "--limit",       help="Limit the number of records to retrieve.", type=int, default=sys.maxint)
    parser_journals.add_argument("-j", "--jobs",        help="Number of download processes to spawn.", type=int)
    parser_journals.add_argument("-f", "--fields",      help="Metadata fields to return, comma separated.\nChoices: name,username,reviewer,journal,sequestered,media_type,description,count,manipulation_units,display_image_url,version,last_updated.", default=None)
    parser_journals.add_argument("-d", "--data",        help="Filter data to post to the API, ex. '{\"manipulation_units\": {\"type\": \"exact\", \"value\": \"2-Unit\"}, \"media_type\": {\"type\": \"exact\", \"value\": \"image\"}}'.")
    parser_journals.add_argument("-r", "--resume",      help="Resume a previous metadata download.  Will start at the line index of the given output file.", action="store_true", default=False)
    parser_journals.add_argument("-i", "--input_file",  help="Optionally download files from .json file rather than through the web API.")

    # /api/cameras/
    parser_cameras = subparsers.add_parser("cameras", help="Retrieve camera metadata and files.")
    parser_cameras.add_argument("credentials",        help="User credentials, in format 'username:password'.")
    parser_cameras.add_argument("output_directory",   help="Directory to save metadata and associated files.")
    parser_cameras.add_argument("-l", "--limit",      help="Limit the number of records to retrieve.", type=int, default=sys.maxint)
    parser_cameras.add_argument("-j", "--jobs",       help="Number of download processes to spawn.", type=int)
    parser_cameras.add_argument("-f", "--fields",     help="Metadata fields to return, comma separated.\nChoices: hp_device_local_id,hp_camera_model,exif,calibrations,affiliation,camera_edition,camera_type,camera_sensor,camera_description,camera_lens_mount,camera_firmware,camera_version,sequestered,high_provenance,available.", default=None)
    parser_cameras.add_argument("-d", "--data",       help="Filter data to post to the API, ex. '{\"high_provenance\": {\"type\": \"exact\", \"value\": \"true\"}, \"available\": {\"type\": \"exact\", \"value\": \"true\"}}'.")
    parser_cameras.add_argument("-m", "--media",      help="Download the media associated with the camera as well.  Note that this requires asking for the 'hp_device_local_id' field.", action="store_true", default=False)
    parser_cameras.add_argument("-r", "--resume",     help="Resume a previous metadata download.  Will start at the line index of the given output file.", action="store_true", default=False)
    parser_cameras.add_argument("-i", "--input_file", help="Optionally download files from .json file rather than through the web API.")

    # global args
    args        = parser.parse_args()
    subcommand  = args.subcommand
    credentials = args.credentials.split(':')
    directory   = args.output_directory
    limit       = args.limit
    jobs        = args.jobs if args.jobs else multiprocessing.cpu_count()-1
    fields      = args.fields
    data        = get_data(args.data)
    kwargs      = { "subcommand": subcommand }

    # Check where we are in the download
    if args.resume and os.path.exists(os.path.join(directory, subcommand, "metadata.json")) and not args.input_file:
        with open(os.path.join(directory, subcommand, "metadata.json"), 'r') as infile:
            start_idx = sum(1 for line in infile)
        start_page = start_idx/1000 + 1
        kwargs["resume_idx"] = start_idx - (start_page-1)*1000
    else:
        start_idx  = 0
        start_page = 1
        kwargs["resume_idx"] = 0

    start_page = start_idx/1000 + 1
    if start_page > 1:
        print("Resuming download at page %d" % start_page)

    # subcommands
    mkdir_p(directory)
    mkdir_p(os.path.join(directory, subcommand))
    headers          = get_headers(credentials)
    download_pool    = multiprocessing.Pool(jobs)
    download_results = []
    download_args    = (download_pool, download_results)
    if subcommand == "media":
        mkdir_p(os.path.join(directory, subcommand, "images"))
        mkdir_p(os.path.join(directory, subcommand, "videos"))
        mkdir_p(os.path.join(directory, subcommand, "audio"))
        mkdir_p(os.path.join(directory, subcommand, "model"))

        url       = "https://medifor.rankone.io/api/images/filters/?page_size=1000%s%s" % (("&fields=%s" % fields) if fields else "", ("&page=%d" % start_page) if start_page > 1 else "")
        count_url = "https://medifor.rankone.io/api/images/count/"

    elif subcommand == "journals":
        mkdir_p(os.path.join(directory, subcommand, "archives"))
        mkdir_p(os.path.join(directory, subcommand, "probes"))

        url       = "https://medifor.rankone.io/api/journals/filters/?page_size=1000%s%s" % (("&fields=%s" % fields) if fields else "", ("&page=%d" % start_page) if start_page > 1 else "")
        count_url = url

    else:
        mkdir_p(os.path.join(directory, subcommand, "prnu"))
        if args.media:
            kwargs["media"] = True
            mkdir_p(os.path.join(directory, subcommand, "media"))
            mkdir_p(os.path.join(directory, subcommand, "media", "images"))
            mkdir_p(os.path.join(directory, subcommand, "media", "videos"))
            mkdir_p(os.path.join(directory, subcommand, "media", "audio"))
            mkdir_p(os.path.join(directory, subcommand, "media", "model"))
        else:
            kwargs["media"] = False

        url       = "https://medifor.rankone.io/api/cameras/filters/?page_size=1000%s%s" % (("&fields=%s" % fields) if fields else "", ("&page=%d" % start_page) if start_page > 1 else "")
        count_url = url

    start_time = time.time()
    if args.input_file:
        get_from_files(args.input_file, directory, headers, download_args, **kwargs)
    else:
        # Get the total
        response = requests.post(count_url, headers=headers, data=json.dumps(data))
        if response.status_code != requests.codes.ok:
            response.raise_for_status()
        jsonResponse = response.json()
        total = jsonResponse['count'] if jsonResponse['count'] < limit else limit

        print("Downloading metadata for %d %s." % (total, "pieces of media" if subcommand == "media" else subcommand))

        count = start_idx
        errs  = 0
        metadata_file = open(os.path.join(directory, subcommand, "metadata.json") , 'a')
        while url and count < total and errs < 10:
            errs, count, url = get_response(errs, count, total, url, data, metadata_file, directory, headers, download_args, **kwargs)
            kwargs["resume_idx"] = 0

            if count > 0:
                rate = count / (time.time() - start_time)
                left = (total - count) / rate / 3600
                print ("Retrieved: %d\tTotal: %d (%.1f%%)\tRate: %f/s\tRemaining: %f hrs" % (count, total, count/(total*1.0)*100, rate, left))

        print("Finished downloading metadata for %d %s." % (total, "pieces of media" if subcommand == "media" else subcommand))
        metadata_file.close()

    download_pool.close()
    print("Finishing up downloads...")
    total_downloads = len(download_results)
    while True:
        incomplete = sum(1 for x in download_results if not x.ready())
        if incomplete == 0:
            print("File downloads complete.")
            break

        finished  = total_downloads - incomplete
        if finished > 0:
            rate      = finished / (time.time() - start_time)
            time_left = (total_downloads - finished) / rate / 3600
            print("Downloaded: %d\tTotal: %d (%.1f%%)\tRate: %f/s\tRemaining: %f hrs" % (finished, total_downloads, finished/float(total_downloads)*100, rate, time_left))
        time.sleep(10)

    download_pool.join()
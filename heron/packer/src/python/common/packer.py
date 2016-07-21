"""Package module defines the interfaces of package management tool needs to implement"""
import sys

from heron.common.src.python.color import Log
from heron.packer.src.python.common import constants
from heron.packer.src.python.common import utils

class Packer(object):
  """Package interface"""
  def add_version(self, args):
    """add a package with 'args' information"""
    raise NotImplementedError("add_version is not implemented")

  def download(self, args):
    """download a package referenced by 'args'"""
    raise NotImplementedError("download is not implemented")

  def delete_version(self, args):
    """delete a package referenced by 'args'"""
    raise NotImplementedError("delete_version is not implemented")

  def list_packages(self, args):
    """list all packages referenced by 'args'"""
    raise NotImplementedError("list_packages is not implemented")

  def list_versions(self, args):
    """list all versions of a package referenced by 'args'"""
    raise NotImplementedError("list_versions is not implemented")

  def set_live(self, args):
    """set a package's version to 'live'"""
    raise NotImplementedError("set_live is not implemented")

  def unset_live(self, args):
    """unset the 'live' tag on a package"""
    raise NotImplementedError("unset_live is not implemented")

  def show_version(self, args):
    """show the basic information for package's version"""
    raise NotImplementedError("show_version is not implemented")

  def show_live(self, args):
    """show the basic information for package's 'live' version"""
    raise NotImplementedError("show_live is not implemented")

  def show_latest(self, args):
    """show the basic information for package's 'latest' version"""
    raise NotImplementedError("show_latest is not implemented")

  def clean(self, args):
    """clean the state"""
    raise NotImplementedError("clean is not implemented")

class HeronPacker(Packer):
  """A metastore and blobstore based implementation of Package"""
  def __init__(self, metastore, blobstore):
    self.metastore = metastore
    self.blobstore = blobstore

  def add_version(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    description = args[constants.DESC]
    extra_info = args[constants.EXTRA]
    file_path = args[constants.PKG_PATH]

    # 1. upload file
    successful, store_location = self.blobstore.upload(file_path)
    if not successful:
      Log.error("Failed to upload the package. Bailing out...")
      sys.exit(1)

    # 2. add package version info into metastore
    successful, version = self.metastore.add_pkg_meta(
        role, pkg_name, store_location, description, extra_info)
    if not successful:
      Log.error("Failed to add the meta data. Bailing out...")
      sys.exit(1)

    # 3. return a uri referencing this uploaded package in customized format
    pkg_uri = self.metastore.get_pkg_uri(
        self.blobstore.get_scheme(), role, pkg_name, version, extra_info)
    Log.info("Uploaded package uri: %s" % pkg_uri)
    return pkg_uri

  def download(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    version = args[constants.VERSION]
    extra_info = args[constants.EXTRA]
    dest_path = args[constants.DEST_PATH]

    # find package location
    pkg_location = self.metastore.get_pkg_location(role, pkg_name, version, extra_info)
    if pkg_location is None:
      Log.error("Cannot find requested package. Bailing out...")
      sys.exit(1)

    # download
    if self.blobstore.download(pkg_location, dest_path):
      Log.info("Successfully downloaded package")
    else:
      Log.error("Failed to download pacakge")

  def delete_version(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    version = args[constants.VERSION]
    extra_info = args[constants.EXTRA]

    # find package location
    pkg_location = self.metastore.get_pkg_location(role, pkg_name, version, extra_info)
    if pkg_location is None:
      Log.error("Cannot find requested package. Bailing out...")
      sys.exit(1)

    # update metastore info with following 2 constraints:
    #   live cannot be deleted;
    #   latest needs to be updated if it's deleted
    isSuccess = self.metastore.delete_pkg_meta(role, pkg_name, version, extra_info)
    if not isSuccess:
      Log.error("Failed to update metastore. Bailing out...")
      sys.exit(1)

    # delete the package
    isSuccess = self.blobstore.delete(pkg_location)
    if not isSuccess:
      Log.error("meta info updated but blob file still exists. Can be cleaned with the clean cmd.")

  def list_packages(self, args):
    role = args[constants.ROLE]
    extra_info = args[constants.EXTRA]
    is_raw = args[constants.RAW]

    # get packages from metastore
    packages = self.metastore.get_packages(role, extra_info)

    utils.print_list(packages, is_raw)

  def list_versions(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    extra_info = args[constants.EXTRA]
    is_raw = args[constants.RAW]

    # get versions from metastore
    versions = self.metastore.get_versions(role, pkg_name, extra_info)
    utils.print_list(versions, is_raw)

  def set_live(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    version = args[constants.VERSION]
    extra_info = args[constants.EXTRA]

    # set live in metastore
    if self.metastore.set_tag(constants.LIVE, role, pkg_name, version, extra_info):
      Log.info("Set live on %s/%s/%s success" % (role, pkg_name, version))
    else:
      Log.error("Set live on %s/%s/%s failed" % (role, pkg_name, version))

  def unset_live(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    extra_info = args[constants.EXTRA]

    # unset live in metastore
    if self.metastore.unset_tag(constants.LIVE, role, pkg_name, extra_info):
      Log.info("Unset live on %s/%s success" % (role, pkg_name))
    else:
      Log.error("Unset live one %s/%s failed" % (role, pkg_name))

  def show_version(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    version = args[constants.VERSION]
    extra_info = args[constants.EXTRA]
    is_raw = args[constants.RAW]

    # get package meta from metastore
    pkg_info = self.metastore.get_pkg_meta(role, pkg_name, version, extra_info)
    utils.print_dict(pkg_info, is_raw)

  def show_live(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    extra_info = args[constants.EXTRA]
    is_raw = args[constants.RAW]

    # get live package information from metastore
    live_pkg_info = self.metastore.get_pkg_meta(role, pkg_name, constants.LIVE, extra_info)
    utils.print_dict(live_pkg_info, is_raw)

  def show_latest(self, args):
    role = args[constants.ROLE]
    pkg_name = args[constants.PKG]
    extra_info = args[constants.EXTRA]
    is_raw = args[constants.RAW]

    # get latest package information from metastore
    latest_pkg_info = self.metastore.get_pkg_meta(role, pkg_name, constants.LATEST, extra_info)
    utils.print_dict(latest_pkg_info, is_raw)

  # clean the inconsistency state of package store.
  def clean(self, args):
    pass
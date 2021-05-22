# coding=utf-8
from __future__ import absolute_import

import datetime
import os
import re
from zipfile import ZipFile

import octoprint.filemanager.util
import octoprint.plugin
from octoprint.util import RepeatedTimer


class UltimakerFormatPackagePlugin(octoprint.plugin.SettingsPlugin,
								   octoprint.plugin.AssetPlugin,
								   octoprint.plugin.TemplatePlugin,
								   octoprint.plugin.EventHandlerPlugin,
								   octoprint.plugin.SimpleApiPlugin):

	def __init__(self):
		self._fileRemovalTimer = None
		self._fileRemovalLastDeleted = {}
		self._fileRemovalLastAdded = {}
		self._folderRemovalTimer = None
		self._folderRemovalLastDeleted = {}
		self._folderRemovalLastAdded = {}
		self._waitForAnalysis = False
		self._analysis_active = False
		self.regex_extension = re.compile("\.(?:gco(?:de)?(?:\.ufp)?)$")

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			installed=True,
			installed_version=self._plugin_version,
			inline_thumbnail=False,
			scale_inline_thumbnail=False,
			inline_thumbnail_scale_value="50",
			inline_thumbnail_position_left=False,
			align_inline_thumbnail=False,
			inline_thumbnail_align_value="left",
			state_panel_thumbnail=True,
			state_panel_thumbnail_scale_value="100",
			resize_filelist=False,
			filelist_height="306",
			scale_inline_thumbnail_position=False
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		return dict(
			js=["js/UltimakerFormatPackage.js"],
			css=["css/UltimakerFormatPackage.css"]
		)

	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False, template="UltimakerFormatPackage_settings.jinja2"),
		]

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event not in ["FileAdded", "FileRemoved", "MetadataAnalysisStarted", "MetadataAnalysisFinished",
						 "FolderRemoved", "FolderAdded"]:
			return

		if event == "FolderRemoved" and payload["storage"] == "local":
			self._logger.debug("Folder removed %s" % payload["name"])
			self._folderRemovalLastDeleted[payload["name"]] = payload
			self._folder_removal_timer_start()
		if event == "FolderAdded":
			self._logger.debug("Folder added %s" % payload["name"])
			self._folderRemovalLastAdded[payload["name"]] = payload

		# Hack that deletes uploaded ufp file from upload path
		if event == "FileAdded" and "ufp" in payload["type"]:
			old_name = payload["path"]  # self._settings.global_get_basefolder("uploads") + "/" +
			ufp_file = self.get_plugin_data_folder() + "/" + payload["path"]
			if os.path.exists(ufp_file):
				os.remove(ufp_file)
			self._file_manager.remove_file("local", old_name)
			return
		if event == "MetadataAnalysisStarted" and payload["path"].endswith(".gcode"):
			self._waitForAnalysis = True
			return
		if event == "MetadataAnalysisFinished" and payload["path"].endswith(".gcode"):
			self._waitForAnalysis = False
			return
		if event == "FileAdded" and payload["path"].endswith(".gcode"):
			self._logger.debug("File added %s" % payload["name"])
			self._fileRemovalLastAdded[payload["name"]] = payload
		if event == "FileRemoved" and payload["name"].endswith(".gcode"):
			self._logger.debug("File removed %s" % payload["name"])
			self._fileRemovalLastDeleted[payload["name"]] = payload
			self._file_removal_timer_start()
			return

	##~~ Folder Removal Timer

	def _folder_removal_timer_start(self):
		if self._folderRemovalTimer is None:
			self._logger.debug("Starting removal timer.")
			self._folderRemovalTimer = RepeatedTimer(5, self._folder_removal_timer_task)
			self._folderRemovalTimer.start()

	def _folder_removal_timer_stop(self):
		self._logger.debug("Cancelling timer and setting everything None.")
		if self._folderRemovalTimer is not None:
			self._folderRemovalTimer.cancel()
			self._folderRemovalTimer = None

	def _folder_removal_timer_task(self):
		if self._waitForAnalysis:
			return

		for key in list(self._folderRemovalLastDeleted):
			if self._folderRemovalLastAdded.get(key, False):
				folder_src = self.get_plugin_data_folder() + "/" + self._folderRemovalLastDeleted[key]["path"]
				folder_dest = self.get_plugin_data_folder() + "/" + self._folderRemovalLastAdded[key]["path"]
				self._logger.debug("Folder moved from: {} to: {}".format(folder_src, folder_dest))
				if os.path.exists(folder_src):
					import shutil
					shutil.move(folder_src, folder_dest)
					file_list = self._file_manager.list_files(path= self._folderRemovalLastAdded[key]["path"], recursive=True)
					local_files = file_list["local"]
					results = dict(no_thumbnail=[], no_thumbnail_src=[])
					for file_key, file in local_files.items():
						results = self._process_gcode(local_files[file_key], results)
					self._logger.debug("Scan results: {}".format(results))

				self._folderRemovalLastAdded.pop(key)
			else:
				self._logger.debug("Folder deleted: {}".format(self._folderRemovalLastDeleted[key]["path"]))
				import shutil
				shutil.rmtree(self.get_plugin_data_folder() + "/" + self._folderRemovalLastDeleted[key]["path"],
							  ignore_errors=True)
				self._folderRemovalLastDeleted.pop(key)

		self._folder_removal_timer_stop()
		self._event_bus.fire("UpdatedFiles", {"type": "printables"})

	##~~ File Removal Timer

	def _file_removal_timer_start(self):
		if self._fileRemovalTimer is None:
			self._logger.debug("Starting removal timer.")
			self._fileRemovalTimer = RepeatedTimer(5, self._file_removal_timer_task)
			self._fileRemovalTimer.start()

	def _file_removal_timer_stop(self):
		self._logger.debug("Cancelling timer and setting everything None.")
		if self._fileRemovalTimer is not None:
			self._fileRemovalTimer.cancel()
			self._fileRemovalTimer = None

	def _file_removal_timer_task(self):
		if self._waitForAnalysis:
			return
		for key in list(self._fileRemovalLastDeleted):
			thumbnail = "{}/{}".format(self.get_plugin_data_folder(), self.regex_extension.sub(".png", self._fileRemovalLastDeleted[key]["path"]))
			ufp_file = "{}/{}".format(self.get_plugin_data_folder(), self.regex_extension.sub(".png", self._fileRemovalLastDeleted[key]["path"]))
			gcode_file = "%s/%s" % (self.get_plugin_data_folder(), self._fileRemovalLastDeleted[key]["path"])
			# clean up double slashes
			thumbnail = thumbnail.replace("//", "/")
			ufp_file = ufp_file.replace("//", "/")
			gcode_file = gcode_file.replace("//", "/")
			if self._fileRemovalLastAdded.get(key, False):
				# copy thumbnail to new path and update metadata
				thumbnail_new = "{}/{}".format(self.get_plugin_data_folder(), self.regex_extension.sub(".png", self._fileRemovalLastAdded[key]["path"]))
				thumbnail_new = thumbnail_new.replace("//", "/")
				thumbnail_new_path = os.path.dirname(thumbnail_new)
				self._logger.debug(thumbnail)
				self._logger.debug(thumbnail_new)
				self._logger.debug(thumbnail_new_path)
				if not os.path.exists(thumbnail_new_path):
					os.makedirs(thumbnail_new_path)
				if os.path.exists(thumbnail_new):
					os.remove(thumbnail_new)
				if thumbnail != thumbnail_new and os.path.exists(thumbnail):
					os.rename(thumbnail, thumbnail_new)
				if os.path.exists(thumbnail_new):
					self._logger.debug("Updating thumbnail url.")
					thumbnail_url = "plugin/UltimakerFormatPackage/thumbnail/{}?{:%Y%m%d%H%M%S}".format(self.regex_extension.sub(".png", self._fileRemovalLastAdded[key]["path"]), datetime.datetime.now()).replace("//", "/")
					self._file_manager.set_additional_metadata("local", self._fileRemovalLastAdded[key]["path"],
															   "thumbnail", thumbnail_url, overwrite=True)
					self._file_manager.set_additional_metadata("local", self._fileRemovalLastAdded[key]["path"],
															   "thumbnail_src", self._identifier, overwrite=True)

				self._fileRemovalLastAdded.pop(key)

			# remove files just in case they are left behind.
			if os.path.exists(thumbnail):
				os.remove(thumbnail)
			if os.path.exists(ufp_file):
				os.remove(ufp_file)
			if os.path.exists(gcode_file):
				os.remove(gcode_file)

			self._fileRemovalLastDeleted.pop(key)

		self._file_removal_timer_stop()

	##~~ Utility Functions

	def deep_get(self, d, keys, default=None):
		"""
		Example:
			d = {'meta': {'status': 'OK', 'status_code': 200}}
			deep_get(d, ['meta', 'status_code'])		  # => 200
			deep_get(d, ['garbage', 'status_code'])	   # => None
			deep_get(d, ['meta', 'garbage'], default='-') # => '-'
		"""
		assert type(keys) is list
		if d is None:
			return default
		if not keys:
			return d
		return self.deep_get(d.get(keys[0]), keys[1:], default)

	##~~ SimpleApiPlugin mixin

	def _process_gcode(self, gcode_file, results=[]):
		self._logger.debug(gcode_file["path"])
		if gcode_file.get("type") == "machinecode":
			self._logger.debug(gcode_file.get("thumbnail"))
			if gcode_file.get("path", False):
				png_path = self.regex_extension.sub(".png", gcode_file["path"])
				full_path = self.get_plugin_data_folder() + "/" + png_path
				self._logger.debug("Checking if {} exists".format(full_path))
				if os.path.exists(full_path):
					results["no_thumbnail_src"].append(gcode_file["path"])
					self._logger.debug("Setting metadata for %s" % gcode_file["path"])
					thumbnail_url = "plugin/UltimakerFormatPackage/thumbnail/{}?{:%Y%m%d%H%M%S}".format(png_path, datetime.datetime.now()).replace("//", "/")
					self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail", thumbnail_url, overwrite=True)
					self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail_src", self._identifier, overwrite=True)
				elif gcode_file.get("thumbnail_src") == self._identifier:
					results["no_thumbnail"].append(gcode_file["path"])
					self._logger.debug("Removing metadata for %s" % gcode_file["path"])
					self._file_manager.remove_additional_metadata("local", gcode_file["path"], "thumbnail_src")
					self._file_manager.remove_additional_metadata("local", gcode_file["path"], "thumbnail")
				else:
					results["no_thumbnail"].append(gcode_file["path"])
		elif gcode_file.get("type") == "folder" and not gcode_file.get("children") is None:
			children = gcode_file["children"]
			for key, file in children.items():
				self._process_gcode(children[key], results)
		return results

	def get_api_commands(self):
		return dict(crawl_files=[])

	def on_api_command(self, command, data):
		import flask
		from octoprint.server import user_permission
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == "crawl_files":
			self._logger.debug("Crawling Files")
			file_list = self._file_manager.list_files(recursive=True)
			local_files = file_list["local"]
			results = dict(no_thumbnail=[], no_thumbnail_src=[])
			for key, file in local_files.items():
				results = self._process_gcode(local_files[key], results)
			return flask.jsonify(results)

	##-- UFP upload extenstion tree hook
	def get_extension_tree(self, *args, **kwargs):
		return dict(
			machinecode=dict(
				ufp=["ufp"]
			)
		)

	##~~ UFP upload preprocessor hook
	def ufp_upload(self, path, file_object, links=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
		ufp_extensions = [".ufp"]
		name, extension = os.path.splitext(file_object.filename)
		if extension in ufp_extensions:
			ufp_filename = self.get_plugin_data_folder() + "/" + path
			png_filename = ufp_filename.replace(".ufp", ".png")
			gco_filename = ufp_filename.replace(".ufp", ".gcode")
			ufp_filepath = os.path.dirname(ufp_filename)

			if not os.path.exists(ufp_filepath):
				os.makedirs(ufp_filepath)

			file_object.save(ufp_filename)
			with ZipFile(ufp_filename, 'r') as zipObj:
				try:
					with open(png_filename, 'wb') as thumbnail:
						thumbnail.write(zipObj.read("/Metadata/thumbnail.png"))
				except KeyError:
					png_filename = None
				with open(gco_filename, 'wb') as f:
					f.write(zipObj.read("/3D/model.gcode"))

			file_wrapper = octoprint.filemanager.util.DiskFileWrapper(path.replace(".ufp", ".gcode"), gco_filename,
																	  move=True)
			uploaded_file = self._file_manager.add_file("local", file_wrapper.filename, file_wrapper,
														allow_overwrite=True)

			if png_filename:
				self._logger.debug('Adding thumbnail url to metadata')
				thumbnail_path = path.replace(".ufp", ".png")
				thumbnail_url = "plugin/UltimakerFormatPackage/thumbnail/{}?{:%Y%m%d%H%M%S}".format(thumbnail_path, datetime.datetime.now())
				self._file_manager.set_additional_metadata("local", uploaded_file, "thumbnail", thumbnail_url, overwrite=True)
				self._file_manager.set_additional_metadata("local", uploaded_file, "thumbnail_src", self._identifier, overwrite=True)

			return octoprint.filemanager.util.DiskFileWrapper(path, ufp_filename)
		return file_object

	##~~ Routes hook
	def route_hook(self, server_routes, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		return [
			(r"thumbnail/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
														   as_attachment=False,
														   path_validation=path_validation_factory(
															   lambda path: not is_hidden_path(path), status_code=404)))
		]

	def additional_excludes_hook(self, excludes, *args, **kwargs):
		if "uploads" in excludes:
			return ["."]
		return []

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			UltimakerFormatPackage=dict(
				displayName="Cura Thumbnails",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="jneilliii",
				repo="OctoPrint-UltimakerFormatPackage",
				current=self._plugin_version,
				stable_branch=dict(
					name="Stable", branch="master", comittish=["master"]
				),
				prerelease_branches=[
					dict(
						name="Release Candidate",
						branch="rc",
						comittish=["rc", "master"],
					)
				],

				# update method: pip
				pip="https://github.com/jneilliii/OctoPrint-UltimakerFormatPackage/archive/{target_version}.zip"
			)
		)


__plugin_name__ = "Cura Thumbnails"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = UltimakerFormatPackagePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.filemanager.extension_tree": __plugin_implementation__.get_extension_tree,
		"octoprint.filemanager.preprocessor": __plugin_implementation__.ufp_upload,
		"octoprint.server.http.routes": __plugin_implementation__.route_hook,
		"octoprint.plugin.backup.additional_excludes": __plugin_implementation__.additional_excludes_hook
	}

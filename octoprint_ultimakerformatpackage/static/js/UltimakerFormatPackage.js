/*
 * View model for OctoPrint-UltimakerFormatPackage
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function() {
	function UltimakerformatpackageViewModel(parameters) {
		var self = this;

		self.settingsViewModel = parameters[0];
		self.filesViewModel = parameters[1];

		self.onAllBound = function(){
			console.log(self.filesViewModel);
		}
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: UltimakerformatpackageViewModel,
		dependencies: ["settingsViewModel", "filesViewModel"],
		elements: []
	});
});

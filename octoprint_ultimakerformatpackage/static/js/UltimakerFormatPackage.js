/*
 * View model for OctoPrint-UltimakerFormatPackage
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function() {
	function UltimakerformatpackageViewModel(parameters) {
		var self = this;
		self.current_file = ko.observable('/static/img/tentacle-20x20.png');

		self.settingsViewModel = parameters[0];
		self.filesViewModel = parameters[1];

		self.filesViewModel.open_thumbnail = function(data) {
			if(data.name.indexOf('.ufp.gcode') > 0){
				var thumbnail_url = '/plugin/UltimakerFormatPackage/' + data.name.replace('.ufp.gcode','.png');
				console.log(thumbnail_url);
				self.current_file(thumbnail_url);
				$('div#thumbnail_viewer').modal("show");
			}
		}

		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }, css: {hidden: name.indexOf(\'.ufp.gcode\') < 0}" title="Show Thumbnail"><i class="fa fa-image"></i></div>';

			$("#files_template_machinecode").text(function () {
				return $(this).text().replace(regex, '<div class="btn-group action-buttons">$1	' + template + '></div>');
			});
		});
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: UltimakerformatpackageViewModel,
		dependencies: ['settingsViewModel', 'filesViewModel'],
		elements: ['div#thumbnail_viewer']
	});
});

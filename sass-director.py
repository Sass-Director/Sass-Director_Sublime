import os
import re
import sublime
import platform
import sublime_plugin


class SassDirectorBase(sublime_plugin.WindowCommand):
    root_path = ""
    manifest_path = ""
    manifest_file = ""
    strip_list = [';', '@import', '\'', '\"']

    def buildPaths(self):
        """
        @function: buildPaths
        @description: Defines the Root Path and Files/Directories in the Root
        """
        folders = self.window.folders()
        view = self.window.active_view()

        self.root_path = folders[0]
        self.manifest_file = view.file_name()

        if(platform.system() is "Windows"):
            self.manifest_path = \
                self.manifest_file[:self.manifest_file.rfind('\\')]
        else:
            self.manifest_path = \
                self.manifest_file[:self.manifest_file.rfind('/')]

    def stripImport(self, line):
        """
        @function: pruneImport
        @parameters: line: {str}
        @description: Removes unnecessary information from the line
        """
        for delimeter in self.strip_list:
            line = line.replace(delimeter, '')
        return line.strip()

    @staticmethod
    def expandImports(imports):
        """
        @function: expandImports
        @parameters: imports: {List}
        @description: Expands the list of imports into an array of strings.
                      Each entry in the array is like follows:
        ['{root_folder}', '{folder_in_root_folder}', ... , 'filename']
        """
        paths = []
        for e in imports:
            path = [e.split('/') if '/' in e else e.split('\\')][0]
            paths.append(path)
        return paths

    def generateDirectories(self, dirs, view):
        # Each entry is a directory structure
        print(dirs)
        for d in dirs:
            file_name = '_' + d.pop(len(d)-1)
            os.chdir(self.manifest_path)
            for directory in d:
                if directory not in os.listdir('.'):
                    os.mkdir(directory)
                    os.chdir(directory)
                    print("Made directory:", directory)
                    print("Now at:", end="")
                    print(os.path.dirname(os.path.realpath(__file__)))
                else:
                    os.chdir(directory)
                    print("WARNING: Directory already exists")
            os.chdir(self.manifest_path)
            [os.chdir(directory) for directory in d]
            # Change to associated directory
            f = open(file_name + '.scss', 'w')
            print("Wrote new scss file:", file_name)
            f.close()

    def generateSassFromManifest(self):
        self.buildPaths()

        view = self.window.active_view()
        body = view.substr(sublime.Region(0, view.size()))
        lines = body.split('\n')

        imports = []
        # Grab Import Lines
        for line in lines:
            if re.match('^@import', line):
                imports.append(self.stripImport(line))
        dirs = self.expandImports(imports)
        self.generateDirectories(dirs, view)
        print("Done! Refreshing folder list...")
        view.run_command('refresh_folder_list')

# ================================================
# ================== Commands ====================
# ================================================


class SassDirectorGenerateCommand(SassDirectorBase):
    def run(self):
        self.generateSassFromManifest()


# ================================================
# ================================================

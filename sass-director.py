import os
import re
import json
import base64
import sublime
import platform
import sublime_plugin

# ====================================================== #
# ====================================================== #

def test_valid_file(view):
    pattern = re.compile('\.(scss|sass)$')
    print(pattern.search(view.file_name()))
    if(pattern.search(view.file_name()) is not None):
        return True
    else:
        return False


def extract_imports(body):
    pattern = re.compile(r'^@import')
    imports = map(lambda line: None if pattern.search(line) is
                  None else line, body.split('\n'))
    imports = [x for x in imports if x is not None]
    return imports


def encrypt_manifest(manifest):
    json_manifest = json.dumps(manifest)
    return base64.b64encode(bytes(json_manifest, 'UTF-8')).decode('UTF-8')


def decrypt_manifest(crypt):
    decrypted_json = base64.b64decode(crypt.encode('UTF-8'))
    return json.loads(decrypted_json.decode('UTF-8'))


def store_manifest(manifest):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, 'manifests.json'), 'r+') as storage:
        contents = json.loads(storage.read())
        # If it has been stored before, ask if we should overwrite
        if(contents.get(manifest.get('name')) is not None):
            ans = sublime.yes_no_cancel_dialog(
                manifest.get('name') + ' already exists in storage.\n' +
                'Would you like to overwrite it?', 'Overwrite', 'Keep')
            if(ans is not 1):
                sublime.status_message('Exited Sass-Director: Save Manifest')
                return
        # Otherwise continue with write
        contents[manifest.get('name')] = encrypt_manifest(manifest)
        # Rewrite the file with our new JSON array
        storage.seek(0)
        storage.truncate()
        storage.write(json.dumps(contents, indent=4, sort_keys=True))
        sublime.status_message('Saved ' + manifest.get('name') +
                               ' to Sass-Director')


# ====================================================== #
# ====================================================== #


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


class SD_SaveManifestFile(sublime_plugin.WindowCommand):
    manifest = {}

    def save(self, name):
        view = self.window.active_view()

        self.manifest['name'] = name
        self.manifest['body'] = view.substr(sublime.Region(0, view.size()))
        self.manifest['imports'] = extract_imports(self.manifest['body'])
        crypt = encrypt_manifest(self.manifest)
        store_manifest(self.manifest)

    def execute(self):
        view = self.window.active_view()
        # Verify its a Sass/Scss file
        if(test_valid_file(view) is False):
            sublime.error_message(view.file_name() +
                                  ' is not a valid Sass/Scss file')
        else:
            self.window.show_input_panel('Please name this manifest:',
                                         '', self.save, None, None)


class SD_OpenManifestFile(sublime_plugin.WindowCommand):
    manifests = {}
    manifest_names = []

    def open_manifest(self, idx):
        crypt = self.manifests.get(self.manifest_names[idx])
        manifest = decrypt_manifest(crypt)
        new_file = self.window.new_file()
        print(vars(new_file))
        new_file.run_command('sass_director_insert_manifest',
                             {'manifest': manifest})

    def get_manifests(self):
        current_dir = os.path.dirname(os.path.join(__file__))
        with open(os.path.join(current_dir, 'manifests.json'), 'r') as storage:
            manifests = json.loads(storage.read())
            return manifests

    def execute(self):
        self.manifests = self.get_manifests()
        self.manifest_names = [x for x in self.manifests.keys()]
        self.window.show_quick_panel(self.manifest_names,
                                     self.open_manifest)

# ================================================
# ================== Commands ====================
# ================================================


class SassDirectorGenerateCommand(SassDirectorBase):
    def run(self):
        self.generateSassFromManifest()


class SassDirectorSaveManifestCommand(SD_SaveManifestFile):
    def run(self):
        self.execute()


class SassDirectorOpenManifestCommand(SD_OpenManifestFile):
    def run(self):
        self.execute()


class SassDirectorInsertManifestCommand(sublime_plugin.TextCommand):
    def run(self, edit, manifest):
        window = sublime.active_window()
        window.active_view().insert(edit, 0, manifest.get('body'))

# ================================================
# ================================================

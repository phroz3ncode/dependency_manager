# Dependency Manager
*"Your vars are broken, scattered, and lost... but together we can fix them."*
***
#### Dependency_manager is and always has been GPLv3 and is 100% free. Donations are not accepted.
***

**What is Dependency Manager?**  
Dependency manager is a highly flexible tool for indexing, organizing, repairing, optimizing and generally
maintaining .var files. While this tool provides a great deal of functionality, some of its features should
be viewed as complex, and it can result in potentially unusable vars if used improperly.

**!!! DISCLAIMER !!!**  
Vars are VERY complex. There are a tremendous amount of correct and incorrectly built vars. Dependency manager
features a verbose suite of complex **and destructive** tools. These tools can be amazing when they work correctly
but you should always be careful when performing destructive actions on vars. If you are unsure it is best to backup
any files first. Dependency manager will NEVER directly update a var in the cold storage, but it can shuffle the files
around. I make every effort to test the functionality, but people are always finding creative ways to break new vars
that I can't even imagine how they did it.

### Building Dependency Manager
Dependency manager is written and built on Python 3.10. It is recommended to use a virtual environment, but not
required for building this tool. A Makefile is included for ease of use, and is compatible git `git bash` for
windows, which is the recommended way to build.

#### Setup
1. Download and install python 3.11+ from https://www.python.org/
2. Install `git bash` from https://gitforwindows.org/
3. Add `make` to `git bash`: https://gist.github.com/evanwill/0207876c3243bbb6863e65ec5dc3f058
   * Download `make-x.x.x-without-guile-w32-bin.zip` from https://sourceforge.net/projects/ezwinports/files/
   * Open your `git bash` folder in Windows (e.g. `C:\Program Files\Git`)
   * Extract the contents of the zip to this folder, but **do not overwrite any files**
4. Open your `git bash` shell on windows and navigate to a folder that will hold your files (e.g. `cd ~`)
5. Download/clone this repository (e.g. `git clone https://github.com/phroz3ncode/dependency_manager.git`)
6. (Optional) Setup and create a new virtual environment (e.g. `mkvirtualenv dependency_manager`)
   * You will need to install virtualenv to do this, you can also use an alternative virtual env setup.

#### Configuring the environment and building the app
1. Run `make reqs` to install the required dependencies
2. Run `make build-quick` to build the tool using the `.spec` file. The resulting `.exe` will appear in the `dist/Windows` folder.
3. You can use `make build-full` to rebuild an exe from scratch.

#### Developing Dependency Manager
Setup a debug environment with the following:
- script path: `dependency_manager\depmanager\run_var.py`
- environment variables:
  - `LOCAL_PATH=<DISK LETTER>:\\path\\to\\vam\\AddonPackages`
  - `REMOTE_PATH=\\<server_ip>\\vam\\AddonPackages` OR `REMOTE_PATH=<DISK LETTER>:\\path\\to\\storage\\AddonPackages`

### Using Dependency Manager
Dependency manager features a LOT of functionality. I will expand on this section in the future.

Basic functionality:
- Create an index of all of your var files in a remote location.
- Automatically categorize vars by type and into folders.
- Synchronize any missing files to your local AddonPackages folder.
- Provide an image based organization system for organizing files to folders.
- Provide a way to quickly organize used and unused vars into separate directories.
- Track and filter required versions. If you don't need a version then it will help you remove it.
- Automatically import vars from your local AddonPackages into a remote location.
- Repair and Compress var files on import.
- Repair broken vars or broken and unoptimized metadata files.
- Provide multiple ways of synchronizing just the files you want to the local AddonPackages.

I recommend creating a small collection and playing around with the functionality until I have more time to update a wiki or howto.

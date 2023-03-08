# Dependency Manager
*"Your vars are broken, scattered, and lost... but together we can fix them."*
***
#### Dependency_manager is and always has been GPLv3 and is 100% free. Donations are not accepted.
***

**What is Dependency Manager?**  
Dependency manager is a highly flexible tool for indexing, organizing, repairing, optimizing and generally
maintaining .var files. While this tool provides a great deal of functionality, some of its features should
be viewed as complex, and it can result in potentially unusable vars if used improperly.

### Building Dependency Manager
Dependency manager is written and built on Python 3.10. It is recommended to use a virtual environment, but not
required for building this tool. A Makefile is included for ease of use, and is compatible git `git bash` for
windows, which is the recommended way to build.

#### Setup
1. Download and install python 3.10+ from https://www.python.org/
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
2. (Optional) You can run `make clean` to remove and previous build trash leftover form the build process
3. Run `make build` to build the tool. The resulting `.exe` will appear in the `dist` folder.

### Using Dependency Manager
Dependency manager features a LOT of functionality. I will expand on this section in the future.
import os
import sys
import textwrap

from conan import ConanFile, conan_version
from conan.tools.files import copy, get, rmdir, save, replace_in_file
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=1.52.0"


class MesonConan(ConanFile):
    name = "meson"
    version = "1.6.0"
    description = "a project to create the best possible next-generation build system"
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/mesonbuild/meson"
    topics = ("mesonbuild", "build-system")
    package_type = "application"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.conf.get("user.camp.common:use_custom_python", default=False, check_type=str):
            self.requires("cpython/[~{}]@camposs/stable".format(self.conf.get("user.camp.common:use_custom_python", check_type=str)))
        if self.conf.get("tools.meson.mesontoolchain:backend", default="ninja", check_type=str) == "ninja":
            # Meson requires >=1.8.2 as of 1.5
            # https://github.com/mesonbuild/meson/blob/b6b634ad33e5ca9ad4a9d6139dba4244847cc0e8/mesonbuild/backend/ninjabackend.py#L625
            self.requires("ninja/[>=1.10.2 <2]@camposs/stable")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "bin", "test cases"))

        # create wrapper scripts
        save(self, os.path.join(self.package_folder, "bin", "meson.cmd"), textwrap.dedent("""\
            @echo off
            set PYTHONDONTWRITEBYTECODE=1
            CALL python %~dp0/meson.py %*
        """))
        save(self, os.path.join(self.package_folder, "bin", "meson"), textwrap.dedent("""\
            #!/usr/bin/env bash
            meson_dir=$(dirname "$0")
            export PYTHONDONTWRITEBYTECODE=1
            exec "$meson_dir/meson.py" "$@"
        """))

    def finalize(self):
        copy(self, "*", src=self.immutable_package_folder, dst=self.package_folder)
        replace_in_file(self, os.path.join(self.package_folder, "bin", "meson.cmd"),
                        "set PYTHONDONTWRITEBYTECODE=1",
                        '')

        replace_in_file(self, os.path.join(self.package_folder, "bin", "meson"),
                        "export PYTHONDONTWRITEBYTECODE=1",
                        '')
        if self.conf.get("user.camp.common:use_custom_python", default=False, check_type=str):
            cpy_dep = self.dependencies["cpython"]
            py_exe_win = os.path.join(cpy_dep.package_folder, "bin", "python.exe")
            py_exe = os.path.join(cpy_dep.package_folder, "bin", "python3")
            bin_path = os.path.join(cpy_dep.package_folder, "bin")
            lib_path = os.path.join(cpy_dep.package_folder, "lib")
            replace_in_file(self, os.path.join(self.package_folder, "bin", "meson.cmd"),
                            "CALL python %~dp0/meson.py %*",
                            textwrap.dedent(f'''\
                                set PYTHONHOME="{cpy_dep.package_folder}"
                                set PATH="{bin_path}";%PATH%
                                set PYTHONPATH="{lib_path}"
                                CALL {py_exe_win} %~dp0/meson.py %*
                                '''))

            replace_in_file(self, os.path.join(self.package_folder, "bin", "meson"),
                            'exec "$meson_dir/meson.py" "$@"',
                            textwrap.dedent(f'''\
                                export PYTHONHOME="{cpy_dep.package_folder}"
                                export PATH="{bin_path}":$PATH
                                export PYTHONPATH="{lib_path}"
                                exec "{py_exe}" "$meson_dir/meson.py" "$@"
                                '''))


    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == "posix":
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def package_info(self):
        meson_root = os.path.join(self.package_folder, "bin")
        self._chmod_plus_x(os.path.join(meson_root, "meson"))
        self._chmod_plus_x(os.path.join(meson_root, "meson.py"))

        self.cpp_info.builddirs = [os.path.join("bin", "mesonbuild", "cmake", "data")]

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        if Version(conan_version).major < 2:
            self.env_info.PATH.append(meson_root)

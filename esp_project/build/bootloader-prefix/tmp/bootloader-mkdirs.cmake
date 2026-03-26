# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "/root/esp/esp-idf/components/bootloader/subproject")
  file(MAKE_DIRECTORY "/root/esp/esp-idf/components/bootloader/subproject")
endif()
file(MAKE_DIRECTORY
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader"
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix"
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/tmp"
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/src/bootloader-stamp"
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/src"
  "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/src/bootloader-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/src/bootloader-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/data/data/com.termux/files/home/esp-vision-loop/esp_project/build/bootloader-prefix/src/bootloader-stamp${cfgdir}") # cfgdir has leading slash
endif()

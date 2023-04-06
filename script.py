import subprocess
import datetime

format = '%Y/%m/%d %H:%M:%S.%f'

PACK = "./out/pack"  # location of pack binary

username = "edithwu"

N = 5
k = 2


def run(command, out, error="error.out"):
    print(command)
    process = subprocess.Popen(command, shell=True, stdout=open(out, "w"), stderr=open(error, "w"))

    process.wait()

    output = open(out).read()
    error = open(error).read()

    if error != "":
        print(error)

    def calculateTime(label):
        time = datetime.timedelta()
        start = output.find(label + " start")
        while start != -1:
            startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
            end = output.find(label + " start", start)
            endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
            time += endTime - startTime
            start = output.find(label + " end", end)

        return time

    buildTime = calculateTime("build")

    lifecycleTime = calculateTime("lifecycleExecutor")

    pullImageTime = calculateTime("NetWork I/O for pulling image")

    downloadTime = calculateTime("NetWork I/O for downloading")

    saveBuilderTime = calculateTime("I/O for saving builder")

    nonblockingTime = buildTime - lifecycleTime - pullImageTime - downloadTime - saveBuilderTime

    parseImageReferenceTime = calculateTime("parse image reference")

    processAppPathTime = calculateTime("process app path")

    processProxyConfigTime = calculateTime("process proxy config")

    processBuilderNameTime = calculateTime("process builder name")

    getBuilderTime = calculateTime("get builder")

    resolveRunImageTime = calculateTime("resolve run image")

    validateRunImageTime = calculateTime("validate run image")

    processBuildpackTime = calculateTime("process buildpack")

    validateMixinsTime = calculateTime("validate mixins")

    createEphemeralBuilderTime = calculateTime("create ephemeral builder")

    processVolumeTime = calculateTime("process volume")

    getFileFilterTime = calculateTime("get file filter")

    translateRegistryTime = calculateTime("translate registry")

    return {"build": buildTime, "lifecycle": lifecycleTime, "pullImage": pullImageTime, "download": downloadTime,
            "saveBuilder": saveBuilderTime, "non-blocking": nonblockingTime,
            "parseImageReference": parseImageReferenceTime, "processAppPath": processAppPathTime,
            "processProxyConfig": processProxyConfigTime, "processBuilderName": processBuilderNameTime,
            "getBuilder": getBuilderTime, "resolveRunImage": resolveRunImageTime, "validateRunImage": validateRunImageTime,
            "processBuildpack": processBuildpackTime, "validateMixins": validateMixinsTime,
            "createEphemeralBuilder": createEphemeralBuilderTime, "processVolume": processVolumeTime,
            "getFileFilter": getFileFilterTime, "translateRegistry": translateRegistryTime}


def repeat(command, out):
    repeatResult = {"build": datetime.timedelta(0), "lifecycle": datetime.timedelta(0),
                    "pullImage": datetime.timedelta(0),"download": datetime.timedelta(0),
                    "saveBuilder": datetime.timedelta(0), "non-blocking": datetime.timedelta(0),
                    "parseImageReference": datetime.timedelta(0), "processAppPath": datetime.timedelta(0),
                    "processProxyConfig": datetime.timedelta(0), "processBuilderName": datetime.timedelta(0),
                    "getBuilder": datetime.timedelta(0), "resolveRunImage": datetime.timedelta(0),
                    "validateRunImage": datetime.timedelta(0),
                    "processBuildpack": datetime.timedelta(0), "validateMixins": datetime.timedelta(0),
                    "createEphemeralBuilder": datetime.timedelta(0), "processVolume": datetime.timedelta(0),
                    "getFileFilter": datetime.timedelta(0), "translateRegistry": datetime.timedelta(0)
                    }
    for i in range(N):
        result = run(command, out)
        if i < k:
            continue
        else:
            for key in repeatResult.keys():
                repeatResult[key] += result[key]

    for value in repeatResult.values():
        value /= N - k
    return repeatResult


def firstBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    repeatResult = {"build": datetime.timedelta(0), "lifecycle": datetime.timedelta(0),
                    "pullImage": datetime.timedelta(0), "download": datetime.timedelta(0),
                    "saveBuilder": datetime.timedelta(0), "non-blocking": datetime.timedelta(0),
                    "parseImageReference": datetime.timedelta(0), "processAppPath": datetime.timedelta(0),
                    "processProxyConfig": datetime.timedelta(0), "processBuilderName": datetime.timedelta(0),
                    "getBuilder": datetime.timedelta(0), "resolveRunImage": datetime.timedelta(0),
                    "validateRunImage": datetime.timedelta(0),
                    "processBuildpack": datetime.timedelta(0), "validateMixins": datetime.timedelta(0),
                    "createEphemeralBuilder": datetime.timedelta(0), "processVolume": datetime.timedelta(0),
                    "getFileFilter": datetime.timedelta(0), "translateRegistry": datetime.timedelta(0)
                    }
    for i in range(N):
        command = PACK + " build " + imageName + "-" + datetime.datetime.now().strftime("%S.%f") + \
                  " --builder " + builder + " --timestamps -v"
        result = run(command, "first_build.out")
        if i < k:
            continue
        else:
            for key in repeatResult.keys():
                repeatResult[key] += result[key]

    for value in repeatResult.values():
        value /= N - k
    return repeatResult


def laterBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "later_build.out")


def tinyBuild(imageName):
    builder = "paketobuildpacks/builder:tiny"
    command = PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "tiny_build.out")


def cacheImageBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + \
              " --timestamps -v --cache type=build;format=image;name=paketo-demo-app;"
    return repeat(command, "cache_image_build.out")


def neverBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy never --timestamps -v"
    return repeat(command, "never_policy_build.out")


def alwaysBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build " + imageName + " --builder " + builder + " --pull-policy always --timestamps -v"
    return repeat(command, "always_policy_build.out")


def publishBuild(imageName):
    builder = "paketobuildpacks/builder:base"
    command = PACK + " build docker.io/" + username + "/" + imageName + ":latest --builder " + builder + " --publish --timestamps -v"
    return repeat(command, "publish_build.out")


def untrustedBuild(imageName):
    origin = "paketobuildpacks/builder:base"
    builder = "mybuilder:base"
    command = "docker tag " + origin + " " + builder + " && " + \
              PACK + " build " + imageName + " --builder " + builder + " --timestamps -v"
    return repeat(command, "untrusted_build.out")


def main():
    file = open("profiling.csv", "w")
    file.write("condition, build, lifecycle, pullImage, download, saveBuilder, non-blocking\n")

    imageName = "paketo-demo-app"

    def output(taskName, result):
        file.write(taskName + ", " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["pullImage"]) + ", " + str(result["download"]) + ", " + str(result["saveBuilder"]) +
                   str(result["non-blocking"]) + "\n")

    result = firstBuild(imageName)
    output("first build", result)

    result = laterBuild(imageName)
    output("later build", result)

    result = tinyBuild(imageName)
    output("tiny build", result)

    result = cacheImageBuild(imageName)
    output("cache image build", result)

    result = neverBuild(imageName)
    output("never policy build", result)

    result = alwaysBuild(imageName)
    output("always policy build", result)

    result = publishBuild(imageName)
    output("publish build", result)

    result = untrustedBuild(imageName)
    output("untrusted build", result)

    file.close()


if __name__ == "__main__":
    main()

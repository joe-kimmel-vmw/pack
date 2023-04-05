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

    start = output.find("build start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("build end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    buildTime = endTime - startTime

    start = output.find("lifecycleExecutor start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("lifecycleExecutor end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    lifecycleTime = endTime - startTime

    pullImageTime = datetime.timedelta()
    start = output.find("NetWork I/O for pulling image start")
    while start != -1:
        startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
        end = output.find("NetWork I/O for pulling image end", start)
        endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
        pullImageTime += endTime - startTime
        start = output.find("NetWork I/O for pulling image start", end)

    downloadTime = datetime.timedelta()
    start = output.find("NetWork I/O for downloading")
    while start != -1:
        startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
        end = output.find("NetWork I/O for downloading", start)
        endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
        downloadTime += endTime - startTime
        start = output.find("NetWork I/O for downloading", end)

    start = output.find("I/O for saving builder start")
    startTime = datetime.datetime.strptime(output[output.rfind('\n', 0, start):start].strip(), format)
    end = output.find("I/O for saving builder end")
    endTime = datetime.datetime.strptime(output[output.rfind('\n', 0, end):end].strip(), format)
    saveBuilderTime = endTime - startTime

    return {"build": buildTime, "lifecycle": lifecycleTime, "pullImage": pullImageTime, "download": downloadTime,
            "saveBuilder": saveBuilderTime}


def repeat(command, out):
    repeatResult = {"build": datetime.timedelta(0), "lifecycle": datetime.timedelta(0), "pullImage": datetime.timedelta(0),
                    "download": datetime.timedelta(0), "saveBuilder": datetime.timedelta(0)}
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
    repeatResult = {"build": datetime.timedelta(0), "lifecycle": datetime.timedelta(0), "pullImage": datetime.timedelta(0),
                    "download": datetime.timedelta(0), "saveBuilder": datetime.timedelta(0)}
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
    file.write("condition, build, lifecycle, pullImage, download, saveBuilder\n")

    imageName = "paketo-demo-app"

    def output(taskName, result):
        file.write(taskName + ", " + str(result["build"]) + ", " + str(result["lifecycle"]) + ", " +
               str(result["pullImage"]) + ", " + str(result["download"]) + ", " + str(result["saveBuilder"]) + "\n")

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

package build

import (
	"context"
	"math/rand"
	"strings"
	"time"

	"github.com/buildpacks/imgutil"
	"github.com/buildpacks/lifecycle/api"
	"github.com/docker/docker/client"
	"github.com/google/go-containerregistry/pkg/name"
	"github.com/pkg/errors"

	"github.com/buildpacks/pack/internal/builder"
	"github.com/buildpacks/pack/internal/cache"
	"github.com/buildpacks/pack/internal/paths"
	"github.com/buildpacks/pack/internal/style"
	"github.com/buildpacks/pack/logging"
)

var (
	// SupportedPlatformAPIVersions lists the Platform API versions pack supports.
	SupportedPlatformAPIVersions = builder.APISet{api.MustParse("0.3"), api.MustParse("0.4")}
)

type Builder interface {
	Name() string
	UID() int
	GID() int
	LifecycleDescriptor() builder.LifecycleDescriptor
	Stack() builder.StackMetadata
	Image() imgutil.Image
}

type Lifecycle struct {
	builder            Builder
	lifecycleImage     string
	logger             logging.Logger
	docker             client.CommonAPIClient
	appPath            string
	httpProxy          string
	httpsProxy         string
	noProxy            string
	version            string
	platformAPIVersion string
	layersVolume       string
	appVolume          string
	defaultProcessType string
	fileFilter         func(string) bool
	os                 string
	mountPaths         mountPaths
}

func (l *Lifecycle) Builder() Builder {
	return l.builder
}

func (l *Lifecycle) AppPath() string {
	return l.appPath
}

func (l *Lifecycle) AppVolume() string {
	return l.appVolume
}

func (l *Lifecycle) LayersVolume() string {
	return l.layersVolume
}

type Cache interface {
	Name() string
	Clear(context.Context) error
}

func init() {
	rand.Seed(time.Now().UTC().UnixNano())
}

func NewLifecycle(docker client.CommonAPIClient, logger logging.Logger) *Lifecycle {
	l := &Lifecycle{logger: logger, docker: docker}

	return l
}

type LifecycleOptions struct {
	AppPath            string
	Image              name.Reference
	Builder            Builder
	LifecycleImage     string
	RunImage           string
	ClearCache         bool
	Publish            bool
	TrustBuilder       bool
	UseCreator         bool
	HTTPProxy          string
	HTTPSProxy         string
	NoProxy            string
	Network            string
	Volumes            []string
	DefaultProcessType string
	FileFilter         func(string) bool
}

func (l *Lifecycle) Execute(ctx context.Context, opts LifecycleOptions) error {
	err := l.Setup(opts)
	if err != nil {
		return err
	}
	defer l.Cleanup()

	phaseFactory := NewDefaultPhaseFactory(l)

	buildCache := cache.NewVolumeCache(opts.Image, "build", l.docker)

	l.logger.Debugf("Using build cache volume %s", style.Symbol(buildCache.Name()))
	if opts.ClearCache {
		if err := buildCache.Clear(ctx); err != nil {
			return errors.Wrap(err, "clearing build cache")
		}
		l.logger.Debugf("Build cache %s cleared", style.Symbol(buildCache.Name()))
	}

	launchCache := cache.NewVolumeCache(opts.Image, "launch", l.docker)

	if !opts.UseCreator {
		l.logger.Info(style.Step("DETECTING"))
		if err := l.Detect(ctx, opts.Network, opts.Volumes, phaseFactory); err != nil {
			return err
		}

		l.logger.Info(style.Step("ANALYZING"))
		if err := l.Analyze(ctx, opts.Image.Name(), buildCache.Name(), opts.Network, opts.Publish, opts.ClearCache, phaseFactory); err != nil {
			return err
		}

		l.logger.Info(style.Step("RESTORING"))
		if opts.ClearCache {
			l.logger.Info("Skipping 'restore' due to clearing cache")
		} else if err := l.Restore(ctx, buildCache.Name(), opts.Network, phaseFactory); err != nil {
			return err
		}

		l.logger.Info(style.Step("BUILDING"))

		if err := l.Build(ctx, opts.Network, opts.Volumes, phaseFactory); err != nil {
			return err
		}

		l.logger.Info(style.Step("EXPORTING"))
		return l.Export(ctx, opts.Image.Name(), opts.RunImage, opts.Publish, launchCache.Name(), buildCache.Name(), opts.Network, phaseFactory)
	}

	return l.Create(
		ctx,
		opts.Publish,
		opts.ClearCache,
		opts.RunImage,
		launchCache.Name(),
		buildCache.Name(),
		opts.Image.Name(),
		opts.Network,
		opts.Volumes,
		phaseFactory,
	)
}

func (l *Lifecycle) Setup(opts LifecycleOptions) error {
	l.layersVolume = paths.FilterReservedNames("pack-layers-" + randString(10))
	l.appVolume = paths.FilterReservedNames("pack-app-" + randString(10))
	l.appPath = opts.AppPath
	l.builder = opts.Builder
	l.lifecycleImage = opts.LifecycleImage
	l.httpProxy = opts.HTTPProxy
	l.httpsProxy = opts.HTTPSProxy
	l.noProxy = opts.NoProxy
	l.version = opts.Builder.LifecycleDescriptor().Info.Version.String()
	l.platformAPIVersion = opts.Builder.LifecycleDescriptor().APIs.Platform.Supported.Latest().String()
	l.defaultProcessType = opts.DefaultProcessType
	l.fileFilter = opts.FileFilter

	os, err := l.builder.Image().OS()
	if err != nil {
		return err
	}
	l.os = os
	l.mountPaths = mountPathsForOS(l.os)
	return nil
}

func (l *Lifecycle) Cleanup() error {
	var reterr error
	if err := l.docker.VolumeRemove(context.Background(), l.layersVolume, true); err != nil {
		reterr = errors.Wrapf(err, "failed to clean up layers volume %s", l.layersVolume)
	}
	if err := l.docker.VolumeRemove(context.Background(), l.appVolume, true); err != nil {
		reterr = errors.Wrapf(err, "failed to clean up app volume %s", l.appVolume)
	}
	return reterr
}

func randString(n int) string {
	b := make([]byte, n)
	for i := range b {
		b[i] = 'a' + byte(rand.Intn(26))
	}
	return string(b)
}

type mountPaths struct {
	volume    string
	separator string
}

func mountPathsForOS(os string) mountPaths {
	if os == "windows" {
		return mountPaths{
			volume:    `c:`,
			separator: `\`,
		}
	}
	return mountPaths{
		volume:    "",
		separator: "/",
	}
}

func (m mountPaths) join(parts ...string) string {
	return strings.Join(parts, m.separator)
}

func (m mountPaths) layersDir() string {
	return m.join(m.volume, "layers")
}

func (m mountPaths) stackPath() string {
	return m.join(m.layersDir(), "stack.toml")
}

func (m mountPaths) appDirName() string {
	return "workspace"
}

func (m mountPaths) appDir() string {
	return m.join(m.volume, m.appDirName())
}

func (m mountPaths) cacheDir() string {
	return m.join(m.volume, "cache")
}

func (m mountPaths) launchCacheDir() string {
	return m.join(m.volume, "launch-cache")
}

func (m mountPaths) platformDir() string {
	return m.join(m.volume, "platform")
}

const {promisify} = require('util')
const readFileAsync = promisify(require('fs').readFile)
const template = readFileAsync('.github/templates/template.hbs')
const commitTemplate = readFileAsync('.github/templates/commit-template.hbs')

const ignore_emojis = ['🔀', '⏪', '🚨', '🚧', '💚', '👌', '📄', '🧑‍💻', '💸', '🧑💻', '🔖'];
const sections = [
    {
        group: 'breaking_changes',
        label: '💥 Breaking changes',
        emojis: ['💥'],
    },
    {
        group: 'sparkles',
        label: '✨ New',
        emojis: ['✨', '🎉'],
    },
    {
        group: 'changed',
        label: '♻ Changes',
        emojis: ['🎨', '✏️', '⚡', '♻️', '🔧', '👽', '🚚', '🍱', '♿️', '💬', '🗃️', '🚸', '🏗️', '📱', '🔥', '🏷️', '🚩', '🛂', '🦺'],
    },
    {
        group: 'fixed',
        label: '🐛 Bugs',
        emojis: ['🐛', '🚑️', '🩹'],
    },
    {
        group: 'dependencies',
        label: '⬆ Dependencies',
        emojis: ['⬆️', '⬇️', '➕', '➖', '📌'],
    },
    {
        group: 'docs',
        label: '📝 Documentation',
        emojis: ['📝'],
    },
    {
        group: 'business_logic',
        label: '👔 Business logic',
        emojis: ['👔'],
    },
    {
        group: 'other',
        label: '🌱 Other',
        emojis: ['*', '🔒️', '🔐', '👷‍♂️', '👷', '💄', '🚀', '📈', '🌐', '💩', '🔊', '🔇', '⚗️', '🥅', '💫', '🧐', '🩺', '🧱']
    },
];


function makeGroups(commits) {
    if (!commits.length) return []

    function mapCommits(groups) {
        const resultCommits = {};

        commits.forEach((commit) => {
            const relevantGroup = groups.find(({group, emojis, label}) =>
                !ignore_emojis.includes(commit.gitmoji) &&
                (emojis.includes(commit.gitmoji) || emojis.includes('*'))
            );

            if (relevantGroup) {
                if (resultCommits[relevantGroup.group]) {
                    resultCommits[relevantGroup.group].push(commit);
                } else {
                    resultCommits[relevantGroup.group] = [commit];
                }
            }
        })

        return groups
            .map(({group, emojis, label}) => ({
                group,
                label,
                is_dep: group === 'dependencies',
                commits: resultCommits[group] ? resultCommits[group].sort((first, second) =>
                    new Date(second.committerDate) - new Date(first.committerDate)) : [],
            }))
            .filter(group => group.commits.length);
    }

    return mapCommits(sections)
}

module.exports = {
    branches: ["main"],
    tagFormat: "v${version}",
    plugins: [
        [
            'semantic-release-gitmoji',
            {
                releaseRules: {
                    patch: {
                        include: sections.slice(2).map(({emojis}) => emojis).flat(),
                        exclude: ['⬆️', '🔖']
                    },
                },
                releaseNotes: {
                    template,
                    partials: {commitTemplate},
                    helpers: {
                        sections: (commits) => {
                            const flatCommits = [];

                            Object.values(commits).forEach(commitValue => {
                                flatCommits.push(...commitValue);
                            });
                            return makeGroups(flatCommits);
                        },
                        split_by_line: (text) => text.split('\n'),
                    },
                }
            }
        ],
        [
            "@semantic-release/changelog",
            {
                changelogFile: "CHANGELOG.md",
                changelogTitle: '<!--next-version-placeholder-->',
            },
        ],
        [
            "@semantic-release/exec",
            {
                prepareCmd: "uv run pytest && uv build"
            },
        ],
        [
            "@semantic-release/git",
            {
                assets: ["CHANGELOG.md"],
                message: [
                    ':bookmark: v${nextRelease.version}  [skip ci]',
                    '',
                    'Automatically generated'
                ].join('\n')
            },
        ],
        [
            "@semantic-release/github",
            {
                assets: [{path: "dist/*.whl"}, {path: "dist/*.tar.gz"}],
            },
        ],
    ],
};

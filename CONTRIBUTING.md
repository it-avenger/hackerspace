# Contributing
We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github
We use github to:
- host code, 
- track issues and feature requests, and
- accept pull requests.

## Contributing Code: All Code Changes Happen Through Pull Requests (PRs)
Pull requests are the best way to propose changes to the codebase (we use [Github Flow](https://guides.github.com/introduction/flow/index.html)). We actively welcome your pull requests:

1. Fork the repo and create your own [feature branch](https://nvie.com/posts/a-successful-git-branching-model/) from `develop`.
2. Provide full docstrings to any new modules, classes, and methods.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes: `python src/manage.py test src`
5. Make sure your code lints: `flake8 src`
6. If you have to make minor changes (typos, linting), please [squash those little commits](https://www.internalpointers.com/post/squash-commits-into-one-git)
6. [Please pull and rebase](https://coderwall.com/p/7aymfa/please-oh-please-use-git-pull-rebase) before sending your PR: `git pull --rebase`
6. Issue that pull request!
7. Check to make sure your PR [passes its checks on TravisCI](https://travis-ci.org/github/timberline-secondary/hackerspace/pull_requests)
8. Engage in the review of your PR until it is accepted


## Report bugs using Github's [issues](https://github.com/timberline-secondary/hackerspace/issues)
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/timberline-secondary/hackerspace/issues/new/choose); it's that easy!

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can, or a screenshot, or screenrecording, as appropriate
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style
We use Flake8 with [a few exclusions](https://github.com/timberline-secondary/hackerspace/blob/develop/src/.flake8).  

## License
By contributing, you agree that your contributions will be licensed under its [GNU GPL3 License](https://github.com/timberline-secondary/hackerspace/blob/develop/license.txt).

## References
This document was adapted from [briandk's adaption](https://gist.github.com/briandk/3d2e8b3ec8daf5a27a62) of the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md)
